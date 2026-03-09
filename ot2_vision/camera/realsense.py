"""Intel RealSense D435i camera wrapper for aligned RGB+Depth capture."""

import numpy as np

from .frame_data import CameraIntrinsics, FrameData


class RealSenseCamera:
    """Wrapper around Intel RealSense D435i for aligned RGB+Depth capture."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self._pipeline = None
        self._align = None
        self._intrinsics: CameraIntrinsics | None = None
        self._depth_scale: float = 0.001

    def start(self) -> None:
        import pyrealsense2 as rs

        self._pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)

        profile = self._pipeline.start(config)

        # Align depth to color
        self._align = rs.align(rs.stream.color)

        # Get depth scale
        depth_sensor = profile.get_device().first_depth_sensor()
        self._depth_scale = depth_sensor.get_depth_scale()

        # Cache intrinsics from first aligned frame
        aligned_frames = self._align.process(self._pipeline.wait_for_frames())
        color_frame = aligned_frames.get_color_frame()
        intr = color_frame.profile.as_video_stream_profile().intrinsics
        self._intrinsics = CameraIntrinsics(
            width=intr.width,
            height=intr.height,
            fx=intr.fx,
            fy=intr.fy,
            ppx=intr.ppx,
            ppy=intr.ppy,
            model=str(intr.model),
            coeffs=list(intr.coeffs),
        )

    def capture(self) -> FrameData:
        """Capture a single aligned RGB+Depth frame."""
        import pyrealsense2 as rs

        if self._pipeline is None:
            raise RuntimeError("Camera not started. Call start() first.")

        frames = self._pipeline.wait_for_frames()
        aligned = self._align.process(frames)

        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()

        if not depth_frame or not color_frame:
            raise RuntimeError("Failed to capture aligned frames")

        rgb = np.asanyarray(color_frame.get_data())
        depth = np.asanyarray(depth_frame.get_data())

        return FrameData(
            rgb=rgb,
            depth=depth,
            intrinsics=self._intrinsics,
            depth_scale=self._depth_scale,
            timestamp=frames.get_timestamp(),
        )

    def stop(self) -> None:
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None

    @property
    def intrinsics(self) -> CameraIntrinsics | None:
        return self._intrinsics
