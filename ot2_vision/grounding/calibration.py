"""Camera-to-deck calibration using ArUco markers and SVD-based rigid transform."""

import json
from pathlib import Path

import cv2
import numpy as np
from cv2 import aruco

from ..camera.frame_data import FrameData
from .ot2_deck import CALIBRATION_POINTS


class CameraDeckCalibrator:
    """Calibrate camera-to-deck rigid transform using ArUco markers.

    Place 4 ArUco markers (DICT_4X4_50, IDs 0-3, 30mm each) at known
    positions on the OT-2 deck:
        Marker 0: Slot 1 bottom-left  (12.13, 9.0 mm)
        Marker 1: Slot 3 bottom-right (380.87, 9.0 mm)
        Marker 2: Slot 7 top-left     (12.13, 258.0 mm)
        Marker 3: Slot 9 top-right    (380.87, 258.0 mm)
    """

    def __init__(self, marker_size_mm: float = 30.0, aruco_dict_type: int = aruco.DICT_4X4_50):
        self.marker_size = marker_size_mm
        self.aruco_dict = aruco.getPredefinedDictionary(aruco_dict_type)
        self.aruco_params = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        self.transform_cam_to_deck: np.ndarray | None = None

    def detect_markers(self, frame: FrameData) -> dict[int, np.ndarray]:
        """Detect ArUco markers and return their 3D positions in camera frame (mm)."""
        gray = cv2.cvtColor(frame.rgb, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)

        if ids is None:
            return {}

        marker_3d = {}
        for i, marker_id in enumerate(ids.flatten()):
            # Get center pixel of marker
            center = corners[i][0].mean(axis=0)
            u, v = int(center[0]), int(center[1])
            # Deproject to 3D using depth
            point_3d = frame.pixel_to_3d(u, v)
            if point_3d[2] > 0:  # Valid depth
                marker_3d[int(marker_id)] = point_3d * 1000  # convert m → mm

        return marker_3d

    def calibrate(self, frame: FrameData, marker_positions: dict | None = None) -> np.ndarray:
        """
        Compute rigid transform from camera frame to deck frame using SVD/Procrustes.

        Returns 4x4 homogeneous transform matrix. Raises ValueError if <3 markers found.
        """
        if marker_positions is None:
            marker_positions = CALIBRATION_POINTS

        detected = self.detect_markers(frame)

        # Find common markers
        common_ids = set(detected.keys()) & set(marker_positions.keys())
        if len(common_ids) < 3:
            raise ValueError(f"Need at least 3 common markers, found {len(common_ids)}: {common_ids}")

        # Build point correspondences
        sorted_ids = sorted(common_ids)
        pts_cam = np.array([detected[mid] for mid in sorted_ids])
        pts_deck = np.array([marker_positions[mid] for mid in sorted_ids])

        # SVD-based Procrustes: solve for deck = R @ cam + t
        centroid_cam = pts_cam.mean(axis=0)
        centroid_deck = pts_deck.mean(axis=0)

        cam_centered = pts_cam - centroid_cam
        deck_centered = pts_deck - centroid_deck

        H = cam_centered.T @ deck_centered
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # Ensure proper rotation (det = +1, not reflection)
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        t = centroid_deck - R @ centroid_cam

        # Build 4x4 homogeneous transform
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = t

        self.transform_cam_to_deck = T
        return T

    def camera_to_deck(self, point_cam_mm: np.ndarray) -> np.ndarray:
        """Transform a 3D point from camera frame to deck frame (mm)."""
        if self.transform_cam_to_deck is None:
            raise RuntimeError("Not calibrated. Run calibrate() first.")
        p = np.append(point_cam_mm, 1.0)
        return (self.transform_cam_to_deck @ p)[:3]

    def reprojection_error(self, frame: FrameData, marker_positions: dict | None = None) -> float:
        """Compute mean reprojection error in mm after calibration."""
        if self.transform_cam_to_deck is None:
            raise RuntimeError("Not calibrated.")

        if marker_positions is None:
            marker_positions = CALIBRATION_POINTS

        detected = self.detect_markers(frame)
        common_ids = set(detected.keys()) & set(marker_positions.keys())

        errors = []
        for mid in common_ids:
            transformed = self.camera_to_deck(detected[mid])
            expected = marker_positions[mid]
            errors.append(np.linalg.norm(transformed - expected))

        return float(np.mean(errors)) if errors else float("inf")

    def save(self, path: str) -> None:
        """Save calibration matrix to JSON."""
        if self.transform_cam_to_deck is None:
            raise RuntimeError("Not calibrated.")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {"transform_cam_to_deck": self.transform_cam_to_deck.tolist()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load calibration matrix from JSON."""
        with open(path) as f:
            data = json.load(f)
        self.transform_cam_to_deck = np.array(data["transform_cam_to_deck"])
