#!/usr/bin/env python3
"""Interactive camera-to-deck calibration using ArUco markers."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import cv2
from ot2_vision.camera.realsense import RealSenseCamera
from ot2_vision.grounding.calibration import CameraDeckCalibrator
from ot2_vision.config import get_config


def main():
    config = get_config()
    save_path = config.calibration_path

    print("=== OT-2 Camera-to-Deck Calibration ===")
    print()
    print("Place 4 ArUco markers (DICT_4X4_50, 30mm) at these deck positions:")
    print("  Marker 0: Slot 1 bottom-left  (12.13, 9.0 mm)")
    print("  Marker 1: Slot 3 bottom-right  (380.87, 9.0 mm)")
    print("  Marker 2: Slot 7 top-left      (12.13, 258.0 mm)")
    print("  Marker 3: Slot 9 top-right     (380.87, 258.0 mm)")
    print()
    print("Controls: SPACE=calibrate, q=quit")
    print()

    cam = RealSenseCamera(width=1280, height=720)
    cam.start()
    calibrator = CameraDeckCalibrator()

    try:
        while True:
            frame = cam.capture()
            display = frame.rgb.copy()

            # Detect and display markers
            markers = calibrator.detect_markers(frame)
            for mid, pos in markers.items():
                label = f"M{mid}: ({pos[0]:.0f},{pos[1]:.0f},{pos[2]:.0f})mm"
                cv2.putText(display, label, (10, 30 + mid * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            status = f"Markers found: {len(markers)}/4"
            color = (0, 255, 0) if len(markers) >= 3 else (0, 0, 255)
            cv2.putText(display, status, (10, display.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            cv2.imshow("Calibration", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                try:
                    T = calibrator.calibrate(frame)
                    error = calibrator.reprojection_error(frame)
                    print(f"\nCalibration successful!")
                    print(f"Reprojection error: {error:.2f} mm")
                    print(f"Transform matrix:\n{T}")
                    calibrator.save(save_path)
                    print(f"Saved to {save_path}")
                    break
                except ValueError as e:
                    print(f"\nCalibration failed: {e}")
                    print("Make sure at least 3 markers are visible.")
            elif key == ord("q"):
                print("Quit without calibrating.")
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
