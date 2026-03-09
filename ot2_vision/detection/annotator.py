"""Debug visualization: draw detections on camera frames."""

import cv2
import numpy as np

from .detector import Detection


def annotate_frame(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """Draw bounding boxes and labels on a frame. Returns annotated copy."""
    annotated = frame.copy()

    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det.bbox]
        color = (0, 255, 0)

        # Bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Label with confidence
        label = f"{det.class_name} {det.confidence:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw, y1), color, -1)
        cv2.putText(annotated, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        # Center dot
        cv2.circle(annotated, (det.center_x, det.center_y), 4, (0, 0, 255), -1)

    return annotated
