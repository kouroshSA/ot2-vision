#!/usr/bin/env python3
"""Quick test: open RealSense camera, display RGB+Depth, print center depth."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

import cv2
from ot2_vision.camera.realsense import RealSenseCamera


def main():
    print("Starting RealSense D435i camera test...")
    cam = RealSenseCamera(width=1280, height=720)
    cam.start()
    print(f"Camera started. Intrinsics: {cam.intrinsics}")
    print("Press 'q' to quit, 's' to save a frame.")

    frame_count = 0
    try:
        while True:
            frame = cam.capture()
            frame_count += 1

            # Normalize depth for visualization
            depth_vis = cv2.applyColorMap(
                cv2.convertScaleAbs(frame.depth, alpha=0.03),
                cv2.COLORMAP_JET,
            )
            combined = cv2.addWeighted(frame.rgb, 0.6, depth_vis, 0.4, 0)

            # Show center depth
            cy, cx = frame.rgb.shape[0] // 2, frame.rgb.shape[1] // 2
            center_depth = frame.depth_at_pixel(cx, cy)
            cv2.putText(combined, f"Center: {center_depth:.3f}m", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(combined, f"Frame: {frame_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("RealSense Test", combined)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                cv2.imwrite(f"frame_{frame_count:04d}_rgb.png", frame.rgb)
                print(f"Saved frame_{frame_count:04d}_rgb.png")
    finally:
        cam.stop()
        cv2.destroyAllWindows()
        print(f"Camera stopped after {frame_count} frames.")


if __name__ == "__main__":
    main()
