"""Generic webcam capture via OpenCV (works with Insta360 Link 2C and any UVC camera)."""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class WebcamCamera:
    """OpenCV VideoCapture wrapper for USB webcams (RGB only, no depth)."""

    def __init__(self, device_index: int = 0, width: int = 1920, height: int = 1080, fps: int = 30):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        """Open the camera device and configure resolution."""
        self._cap = cv2.VideoCapture(self.device_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera at /dev/video{self.device_index}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Discard a few frames to let auto-exposure settle
        for _ in range(5):
            self._cap.read()

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Webcam started: /dev/video{self.device_index} at {actual_w}x{actual_h}")

    def capture(self) -> np.ndarray:
        """Capture a single frame. Returns (H, W, 3) uint8 BGR array."""
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError("Camera not started. Call start() first.")

        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise RuntimeError("Failed to capture frame from webcam")

        return frame

    def capture_jpeg(self, quality: int = 90) -> bytes:
        """Capture a frame and return it as JPEG bytes (for API transmission)."""
        frame = self.capture()
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            raise RuntimeError("Failed to encode frame as JPEG")
        return buffer.tobytes()

    def stop(self) -> None:
        """Release the camera."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Webcam stopped")
