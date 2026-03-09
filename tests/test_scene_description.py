"""Tests for scene description builder."""

from ot2_vision.protocol.scene_description import build_mock_scene, build_scene_description


def test_build_mock_scene():
    slot_labware = {
        "1": ("96-well plate", "corning_96_wellplate_360ul_flat"),
        "10": ("300ul tip rack", "opentrons_96_tiprack_300ul"),
    }
    desc = build_mock_scene(slot_labware)

    assert "<deck_state>" in desc
    assert "96-well plate" in desc
    assert "Slot 1" in desc
    assert "300ul tip rack" in desc
    assert "Slot 10" in desc
    assert "corning_96_wellplate_360ul_flat" in desc
    assert "front/near" in desc  # slot 1 is near


def test_build_mock_scene_empty():
    desc = build_mock_scene({})
    assert "<deck_state>" in desc


def test_build_scene_description_empty():
    desc = build_scene_description([])
    assert "No labware detected" in desc


def test_build_scene_description_with_objects():
    from ot2_vision.detection.detector import Detection
    from ot2_vision.grounding.ot2_deck import get_slot_by_id
    from ot2_vision.grounding.spatial_resolver import GroundedObject

    slot = get_slot_by_id("5")
    cx, cy = slot.center
    obj = GroundedObject(
        detection=Detection(
            class_id=0,
            class_name="96-well plate",
            confidence=0.92,
            bbox=(100, 100, 300, 300),
            center_px=(200, 200),
        ),
        slot=slot,
        deck_position=(cx, cy, 0.0),
        labware_name="corning_96_wellplate_360ul_flat",
    )

    desc = build_scene_description([obj])
    assert "Slot 5" in desc
    assert "96-well plate" in desc
    assert "92%" in desc
    assert "middle" in desc
