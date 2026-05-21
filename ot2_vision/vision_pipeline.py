"""End-to-end vision-language pipeline: webcam → Claude Vision → protocol → execute."""

import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from .camera.webcam import WebcamCamera
from .config import get_config
from .executor.ot2_client import OT2Client
from .executor.protocol_runner import ProtocolRunner
from .protocol.generator import ProtocolGenerator
from .protocol.validator import ProtocolValidator
from .vision.scene_analyzer import SceneAnalyzer

logger = logging.getLogger(__name__)


class VisionLanguagePipeline:
    """End-to-end pipeline: webcam → Claude Vision analysis → protocol generation → [execution]."""

    def __init__(self, camera_device: int = 0, camera_width: int = 1920, camera_height: int = 1080):
        self.config = get_config()
        self.camera_device = camera_device
        self.camera_width = camera_width
        self.camera_height = camera_height

        self.camera: WebcamCamera | None = None
        self.analyzer: SceneAnalyzer | None = None
        self.generator: ProtocolGenerator | None = None
        self.ot2_client: OT2Client | None = None
        self._active_run_id: str | None = None

    def initialize(self, skip_camera: bool = False, skip_ot2: bool = False) -> None:
        """Initialize all modules."""
        if not skip_camera:
            self.camera = WebcamCamera(
                device_index=self.camera_device,
                width=self.camera_width,
                height=self.camera_height,
            )
            self.camera.start()
            logger.info("Webcam started")

        self.analyzer = SceneAnalyzer(api_key=self.config.anthropic_api_key)
        logger.info("Scene analyzer ready")

        self.generator = ProtocolGenerator(api_key=self.config.anthropic_api_key)
        logger.info("Protocol generator ready")

        if not skip_ot2 and self.config.ot2_host:
            self.ot2_client = OT2Client(host=self.config.ot2_host, port=self.config.ot2_port)
            logger.info(f"OT-2 client: {self.config.ot2_host}:{self.config.ot2_port}")

    def capture_and_analyze(self, image_path: str | None = None) -> tuple[bytes, dict, str]:
        """
        Capture image and analyze with Claude Vision.

        Returns:
            (jpeg_bytes, analysis_dict, scene_text)
        """
        if image_path:
            logger.info(f"Using image file: {image_path}")
            analysis = self.analyzer.analyze_image_file(image_path)
            with open(image_path, "rb") as f:
                jpeg_bytes = f.read()
        else:
            if self.camera is None:
                raise RuntimeError("Camera not initialized")
            logger.info("Capturing image from webcam...")
            jpeg_bytes = self.camera.capture_jpeg(quality=90)
            logger.info("Analyzing image with Claude Vision API...")
            analysis = self.analyzer.analyze_image(jpeg_bytes)

        scene_text = self.analyzer.build_scene_text(analysis)
        logger.info(f"Scene analysis: {len(analysis.get('labware', []))} items detected")
        return jpeg_bytes, analysis, scene_text

    def generate_protocol(self, instruction: str, scene_text: str) -> str:
        """Generate protocol from instruction + scene description."""
        logger.info("Generating protocol with Claude API...")
        return self.generator.generate_from_scene_text(instruction, scene_text)

    def validate_protocol(self, code: str) -> tuple[bool, str]:
        return ProtocolValidator.validate(code)

    def execute_protocol(self, code: str) -> dict:
        """Upload and execute protocol on OT-2 with emergency stop support."""
        if self.ot2_client is None:
            raise RuntimeError("OT-2 client not initialized")

        runner = ProtocolRunner(self.ot2_client)

        def emergency_stop(signum, frame):
            logger.warning("EMERGENCY STOP triggered")
            if self._active_run_id:
                try:
                    self.ot2_client.stop_run(self._active_run_id)
                except Exception as e:
                    logger.error(f"Failed to stop run: {e}")
            sys.exit(1)

        old_handler = signal.signal(signal.SIGINT, emergency_stop)

        try:
            protocol_id = self.ot2_client.upload_protocol(code)
            run_id = self.ot2_client.create_run(protocol_id, poll_analysis=True)
            self._active_run_id = run_id

            self.ot2_client.start_run(run_id)
            status = self.ot2_client.wait_for_run(run_id, timeout=300, poll_interval=2)

            return {"protocol_id": protocol_id, "run_id": run_id, "status": status}
        finally:
            self._active_run_id = None
            signal.signal(signal.SIGINT, old_handler)

    def run(
        self,
        instruction: str,
        execute: bool = False,
        save_path: str | None = None,
        image_path: str | None = None,
    ) -> dict:
        """Full pipeline execution."""
        result = {}

        # 1. Capture + Analyze
        jpeg_bytes, analysis, scene_text = self.capture_and_analyze(image_path)
        result["analysis"] = analysis
        result["scene_text"] = scene_text

        # Save captured image
        if save_path:
            img_save = str(Path(save_path).with_suffix(".jpg"))
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_save = str(Path(self.config.protocols_dir) / f"capture_{ts}.jpg")
        Path(img_save).parent.mkdir(parents=True, exist_ok=True)
        Path(img_save).write_bytes(jpeg_bytes)
        result["captured_image"] = img_save

        # 2. Generate protocol
        code = self.generate_protocol(instruction, scene_text)
        result["protocol_code"] = code

        # 3. Validate
        is_valid, msg = self.validate_protocol(code)
        result["validation"] = {"valid": is_valid, "message": msg}

        # 4. Save protocol
        if save_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(Path(self.config.protocols_dir) / f"vision_protocol_{ts}.py")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(code)
        result["saved_to"] = save_path
        logger.info(f"Protocol saved to {save_path}")

        # 5. Execute (optional)
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
