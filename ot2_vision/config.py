import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    ot2_host: str = field(default_factory=lambda: os.getenv("OT2_IP", "192.168.1.10"))
    ot2_port: int = field(default_factory=lambda: int(os.getenv("OT2_PORT", "31950")))
    yolo_model_path: str = field(default_factory=lambda: os.getenv("YOLO_MODEL_PATH", str(PROJECT_ROOT / "models" / "yolov8m.pt")))
    detection_confidence: float = field(default_factory=lambda: float(os.getenv("DETECTION_CONFIDENCE", "0.5")))
    calibration_path: str = field(default_factory=lambda: os.getenv("CALIBRATION_PATH", str(PROJECT_ROOT / "calibration" / "camera_to_deck.json")))
    protocols_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "protocols"))

    # Reference docs from OpentronsAI server
    opentrons_docs_path: str = field(
        default_factory=lambda: str(Path.home() / "Models" / "opentrons-ai" / "opentrons-ai-server" / "api" / "storage" / "docs")
    )


_config = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
