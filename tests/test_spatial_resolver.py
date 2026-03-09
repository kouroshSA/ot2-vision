"""Tests for spatial resolver."""

from ot2_vision.detection.detector import Detection
from ot2_vision.grounding.ot2_deck import get_slot_by_id
from ot2_vision.grounding.spatial_resolver import (
    GroundedObject,
    get_spatial_description,
    resolve_spatial_reference,
)


def _make_grounded(slot_id: str, class_name: str = "96-well plate", load_name: str = "corning_96_wellplate_360ul_flat") -> GroundedObject:
    """Helper to create a GroundedObject for testing."""
    slot = get_slot_by_id(slot_id)
    cx, cy = slot.center
    return GroundedObject(
        detection=Detection(
            class_id=0,
            class_name=class_name,
            confidence=0.95,
            bbox=(0, 0, 100, 100),
            center_px=(50, 50),
        ),
        slot=slot,
        deck_position=(cx, cy, 0.0),
        labware_name=load_name,
    )


def test_resolve_far_plate():
    near = _make_grounded("1")
    far = _make_grounded("10")
    result = resolve_spatial_reference("far", [near, far])
    assert result is not None
    assert result.slot_id == "10"


def test_resolve_near_plate():
    near = _make_grounded("1")
    far = _make_grounded("10")
    result = resolve_spatial_reference("near", [near, far])
    assert result is not None
    assert result.slot_id == "1"


def test_resolve_left_plate():
    left = _make_grounded("1")
    right = _make_grounded("3")
    result = resolve_spatial_reference("left", [left, right])
    assert result is not None
    assert result.slot_id == "1"


def test_resolve_right_plate():
    left = _make_grounded("1")
    right = _make_grounded("3")
    result = resolve_spatial_reference("right", [left, right])
    assert result is not None
    assert result.slot_id == "3"


def test_resolve_with_type_filter():
    plate = _make_grounded("1", "96-well plate", "corning_96_wellplate_360ul_flat")
    tip_rack = _make_grounded("10", "300ul tip rack", "opentrons_96_tiprack_300ul")
    result = resolve_spatial_reference("far", [plate, tip_rack], labware_type="plate")
    # Only the plate in slot 1 matches "plate" filter
    assert result is not None
    assert result.slot_id == "1"


def test_resolve_no_match_returns_none():
    result = resolve_spatial_reference("far", [], labware_type="plate")
    assert result is None


def test_resolve_front_synonym():
    near = _make_grounded("2")
    far = _make_grounded("8")
    result = resolve_spatial_reference("front", [near, far])
    assert result is not None
    assert result.slot_id == "2"


def test_resolve_back_synonym():
    near = _make_grounded("2")
    far = _make_grounded("8")
    result = resolve_spatial_reference("back", [near, far])
    assert result is not None
    assert result.slot_id == "8"


def test_spatial_description_front_left():
    desc = get_spatial_description((30.0, 40.0, 0.0))
    assert "front" in desc or "near" in desc
    assert "left" in desc


def test_spatial_description_back_right():
    desc = get_spatial_description((300.0, 280.0, 0.0))
    assert "back" in desc or "far" in desc
    assert "right" in desc


def test_spatial_description_middle_center():
    desc = get_spatial_description((196.0, 130.0, 0.0))
    assert "middle" in desc
    assert "center" in desc
