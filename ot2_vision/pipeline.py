"""End-to-end pipeline: camera → detect → ground → generate → execute."""

import logging
from datetime import datetime
from pathlib import Path

from .camera.frame_data import FrameData
from .camera.realsense import RealSenseCamera
from .config import get_config
from .detection.detector import Detection, LabwareDetector
from .executor.ot2_client import OT2Client
from .executor.protocol_runner import ProtocolRunner
from .grounding.calibration import CameraDeckCalibrator
from .grounding.deck_mapper import map_detections_to_deck
from .grounding.spatial_resolver import GroundedObject
from .protocol.generator import ProtocolGenerator
from .protocol.validator import ProtocolValidator

logger = logging.getLogger(__name__)


class VisionProtocolPipeline:
    """End-to-end pipeline: camera → detect → ground → generate → [execute]."""

    def __init__(self):
        self.config = get_config()
        self.camera: RealSenseCamera | None = None
        self.detector: LabwareDetector | None = None
        self.calibrator: CameraDeckCalibrator | None = None
        self.generator: ProtocolGenerator | None = None
        self.ot2_client: OT2Client | None = None

    def initialize(self, skip_camera: bool = False, skip_ot2: bool = False) -> None:
        """Initialize all modules."""
        if not skip_camera:
            self.camera = RealSenseCamera()
            self.camera.start()
            logger.info("Camera started")

        self.detector = LabwareDetector(
            model_path=self.config.yolo_model_path,
            confidence_threshold=self.config.detection_confidence,
        )
        logger.info("Detector loaded")

        self.calibrator = CameraDeckCalibrator()
        calib_path = Path(self.config.calibration_path)
        if calib_path.exists():
            self.calibrator.load(str(calib_path))
            logger.info("Loaded existing calibration")
        else:
            logger.warning("No calibration file found. Run calibration first.")

        self.generator = ProtocolGenerator(api_key=self.config.anthropic_api_key)
        logger.info("Protocol generator ready")

        if not skip_ot2 and self.config.ot2_host:
            self.ot2_client = OT2Client(host=self.config.ot2_host, port=self.config.ot2_port)
            logger.info(f"OT-2 client initialized: {self.config.ot2_host}:{self.config.ot2_port}")

    def capture_and_detect(self) -> tuple[FrameData, list[Detection]]:
        """Capture frame and run detection."""
        if self.camera is None:
            raise RuntimeError("Camera not initialized")
        frame = self.camera.capture()
        detections = self.detector.detect(frame.rgb)
        logger.info(f"Detected {len(detections)} objects")
        return frame, detections

    def ground_detections(self, frame: FrameData, detections: list[Detection]) -> list[GroundedObject]:
        """Map detections to deck slots."""
        if self.calibrator is None or self.calibrator.transform_cam_to_deck is None:
            raise RuntimeError("Calibration not loaded")
        return map_detections_to_deck(detections, frame, self.calibrator)

    def generate_protocol(self, instruction: str, grounded: list[GroundedObject]) -> str:
        """Generate protocol from instruction + visual scene."""
        return self.generator.generate(instruction, grounded)

    def validate_protocol(self, code: str) -> tuple[bool, str]:
        """Validate protocol syntax and structure."""
        return ProtocolValidator.validate(code)

    def execute_protocol(self, code: str, labware_paths: list[str] | None = None) -> dict:
        """Upload and execute protocol on OT-2."""
        if self.ot2_client is None:
            raise RuntimeError("OT-2 client not initialized")
        runner = ProtocolRunner(self.ot2_client)
        return runner.run_protocol(code, labware_paths)

    def run(self, instruction: str, execute: bool = False, save_path: str | None = None) -> dict:
        """
        Full pipeline execution.

        Args:
            instruction: Natural language instruction
            execute: Whether to upload+run on OT-2 (False = demo mode)
            save_path: Where to save the generated protocol
        """
        result = {}

        # 1. Capture + Detect
        frame, detections = self.capture_and_detect()
        result["detections"] = detections

        # 2. Ground
        grounded = self.ground_detections(frame, detections)
        result["grounded_objects"] = grounded

        # 3. Generate
        code = self.generate_protocol(instruction, grounded)
        result["protocol_code"] = code

        # 4. Validate
        is_valid, msg = self.validate_protocol(code)
        result["validation"] = {"valid": is_valid, "message": msg}

        # 5. Save
        if save_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(Path(self.config.protocols_dir) / f"vision_protocol_{ts}.py")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(code)
        result["saved_to"] = save_path
        logger.info(f"Protocol saved to {save_path}")

        # 6. Execute (optional)
        if execute and is_valid:
            try:
                exec_result = self.execute_protocol(code)
                result["execution"] = exec_result
            except Exception as e:
                result["execution"] = {"status": "error", "message": str(e)}
        else:
            result["execution"] = {"status": "skipped"}

        return result

    def cleanup(self) -> None:
        if self.camera:
            self.camera.stop()
