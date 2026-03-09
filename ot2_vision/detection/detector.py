"""YOLOv8-based labware detector."""

from dataclasses import dataclass

import numpy as np

from .labware_classes import get_display_name, get_opentrons_name


@dataclass
class Detection:
    """A single detected object."""

    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) in pixels
    center_px: tuple[float, float]  # (cx, cy) center pixel

    @property
    def center_x(self) -> int:
        return int((self.bbox[0] + self.bbox[2]) / 2)

    @property
    def center_y(self) -> int:
        return int((self.bbox[1] + self.bbox[3]) / 2)

    @property
    def opentrons_name(self) -> str:
        return get_opentrons_name(self.class_id)


class LabwareDetector:
    """YOLOv8-based labware detector."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.conf_threshold = confidence_threshold

    def detect(self, rgb_frame: np.ndarray) -> list[Detection]:
        """Run inference on a single RGB frame. Returns list of detections."""
        results = self.model(rgb_frame, conf=self.conf_threshold, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cls_name = result.names.get(cls_id, get_display_name(cls_id))

                detections.append(
                    Detection(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center_px=((x1 + x2) / 2, (y1 + y2) / 2),
                    )
                )

        return detections
