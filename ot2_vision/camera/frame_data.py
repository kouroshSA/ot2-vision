"""Data structures for camera frames with RGB + depth."""

from dataclasses import dataclass

import numpy as np


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters from RealSense."""

    width: int
    height: int
    fx: float  # focal length x
    fy: float  # focal length y
    ppx: float  # principal point x
    ppy: float  # principal point y
    model: str  # distortion model name
    coeffs: list  # distortion coefficients


@dataclass
class FrameData:
    """A single capture from the RealSense camera (RGB + aligned depth)."""

    rgb: np.ndarray  # (H, W, 3) uint8 BGR
    depth: np.ndarray  # (H, W) uint16 in millimeters
    intrinsics: CameraIntrinsics
    depth_scale: float  # meters per depth unit (typically 0.001)
    timestamp: float  # capture timestamp

    def depth_at_pixel(self, u: int, v: int) -> float:
        """Return depth in meters at pixel (u, v)."""
        return float(self.depth[v, u]) * self.depth_scale

    def pixel_to_3d(self, u: int, v: int) -> np.ndarray:
        """Deproject pixel (u, v) to 3D point in camera frame (meters)."""
        z = self.depth_at_pixel(u, v)
        if z <= 0:
            return np.array([0.0, 0.0, 0.0])
        x = (u - self.intrinsics.ppx) * z / self.intrinsics.fx
        y = (v - self.intrinsics.ppy) * z / self.intrinsics.fy
        return np.array([x, y, z])
