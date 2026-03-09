"""Map detected objects to OT-2 deck slots using calibration + depth."""

from ..camera.frame_data import FrameData
from ..detection.detector import Detection
from ..detection.labware_classes import get_opentrons_name
from .calibration import CameraDeckCalibrator
from .ot2_deck import find_slot, nearest_slot
from .spatial_resolver import GroundedObject


def map_detections_to_deck(
    detections: list[Detection],
    frame: FrameData,
    calibrator: CameraDeckCalibrator,
) -> list[GroundedObject]:
    """
    Map a list of detections to OT-2 deck slots using calibrated camera-to-deck transform.

    For each detection:
    1. Get center pixel → 3D point in camera frame (via depth + intrinsics)
    2. Transform to deck frame using calibration matrix
    3. Find which slot the point falls in

    Returns list of GroundedObject with slot assignments.
    """
    grounded = []

    for det in detections:
        u, v = det.center_x, det.center_y

        # Get 3D position in camera frame (meters)
        point_cam = frame.pixel_to_3d(u, v)
        if point_cam[2] <= 0:
            continue  # No valid depth

        # Transform to deck frame (mm)
        point_cam_mm = point_cam * 1000.0
        point_deck = calibrator.camera_to_deck(point_cam_mm)

        # Find slot
        slot = find_slot(point_deck[0], point_deck[1])
        if slot is None:
            slot = nearest_slot(point_deck[0], point_deck[1])

        grounded.append(
            GroundedObject(
                detection=det,
                slot=slot,
                deck_position=(float(point_deck[0]), float(point_deck[1]), float(point_deck[2])),
                labware_name=get_opentrons_name(det.class_id),
            )
        )

    return grounded
