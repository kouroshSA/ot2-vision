"""Tests for webcam camera module (mocked, no physical camera needed)."""

from unittest.mock import MagicMock, patch

import numpy as np


def test_webcam_capture_returns_bgr_array():
    """WebcamCamera.capture() should return an (H, W, 3) uint8 array."""
    with patch("cv2.VideoCapture") as MockCap:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((1080, 1920, 3), dtype=np.uint8))
        mock_cap.get.return_value = 1920
        MockCap.return_value = mock_cap

        from ot2_vision.camera.webcam import WebcamCamera

        cam = WebcamCamera(device_index=0, width=1920, height=1080)
        cam.start()
        frame = cam.capture()

        assert frame.shape == (1080, 1920, 3)
        assert frame.dtype == np.uint8
        cam.stop()


def test_webcam_capture_jpeg_returns_bytes():
    """WebcamCamera.capture_jpeg() should return valid JPEG bytes."""
    with patch("cv2.VideoCapture") as MockCap:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, img)
        mock_cap.get.return_value = 100
        MockCap.return_value = mock_cap

        from ot2_vision.camera.webcam import WebcamCamera

        cam = WebcamCamera(device_index=0, width=100, height=100)
        cam.start()
        jpeg = cam.capture_jpeg()

        assert isinstance(jpeg, bytes)
        assert len(jpeg) > 0
        assert jpeg[:2] == b"\xff\xd8"  # JPEG magic bytes
        cam.stop()


def test_webcam_raises_if_not_started():
    """Capture should raise RuntimeError if camera not started."""
    from ot2_vision.camera.webcam import WebcamCamera

    cam = WebcamCamera()
    try:
        cam.capture()
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass
