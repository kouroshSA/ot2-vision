#!/usr/bin/env python3
"""Test YOLOv8 detection on a single image file."""

import argparse
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import cv2
from ot2_vision.detection.detector import LabwareDetector
from ot2_vision.detection.annotator import annotate_frame
from ot2_vision.config import get_config


def main():
    parser = argparse.ArgumentParser(description="Test labware detection on an image")
    parser.add_argument("--image", "-i", required=True, help="Path to input image")
    parser.add_argument("--model", "-m", default=None, help="Path to YOLO model weights")
    parser.add_argument("--confidence", "-c", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--output", "-o", default=None, help="Save annotated image to this path")
    args = parser.parse_args()

    config = get_config()
    model_path = args.model or config.yolo_model_path

    print(f"Loading model from {model_path}...")
    detector = LabwareDetector(model_path=model_path, confidence_threshold=args.confidence)

    print(f"Reading image from {args.image}...")
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: could not read image {args.image}")
        sys.exit(1)

    print("Running detection...")
    detections = detector.detect(image)

    print(f"\nFound {len(detections)} detections:")
    for det in detections:
        print(f"  - {det.class_name} ({det.confidence:.0%}) at ({det.center_x}, {det.center_y})")

    # Annotate
    annotated = annotate_frame(image, detections)

    if args.output:
        cv2.imwrite(args.output, annotated)
        print(f"\nSaved annotated image to {args.output}")
    else:
        cv2.imshow("Detections", annotated)
        print("\nPress any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
