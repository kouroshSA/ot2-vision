"""Tests for OT-2 deck geometry."""

from ot2_vision.grounding.ot2_deck import DeckSlot, find_slot, get_slot_by_id, nearest_slot


def test_slot_contains():
    slot = DeckSlot("1", 0.0, 0.0)
    assert slot.contains(64.0, 43.0)  # center
    assert slot.contains(0.0, 0.0)  # origin
    assert slot.contains(128.0, 86.0)  # far corner
    assert not slot.contains(-1.0, 0.0)
    assert not slot.contains(129.0, 0.0)


def test_slot_center():
    slot = DeckSlot("1", 0.0, 0.0)
    cx, cy = slot.center
    assert cx == 64.0
    assert cy == 43.0


def test_find_slot_center_of_slot_1():
    slot = find_slot(64.0, 43.0)
    assert slot is not None
    assert slot.slot_id == "1"


def test_find_slot_center_of_slot_5():
    slot = find_slot(196.5, 133.5)
    assert slot is not None
    assert slot.slot_id == "5"


def test_find_slot_returns_none_outside_deck():
    assert find_slot(-100, -100) is None
    assert find_slot(500, 500) is None


def test_nearest_slot():
    # Point near slot 1 but slightly outside
    slot = nearest_slot(-5.0, -5.0)
    assert slot.slot_id == "1"


def test_nearest_slot_far_corner():
    slot = nearest_slot(330.0, 315.0)
    assert slot.slot_id == "trash"


def test_get_slot_by_id():
    slot = get_slot_by_id("5")
    assert slot is not None
    assert slot.x_origin == 132.5
    assert slot.y_origin == 90.5


def test_get_slot_by_id_invalid():
    assert get_slot_by_id("99") is None


def test_all_12_slots_exist():
    expected = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "trash"]
    for sid in expected:
        assert get_slot_by_id(sid) is not None


def test_slots_do_not_overlap():
    """Verify no two slot centers fall within another slot's bounds."""
    from ot2_vision.grounding.ot2_deck import OT2_SLOTS

    for i, slot_a in enumerate(OT2_SLOTS):
        cx, cy = slot_a.center
        for j, slot_b in enumerate(OT2_SLOTS):
            if i != j:
                assert not slot_b.contains(cx, cy), f"Slot {slot_a.slot_id} center falls inside slot {slot_b.slot_id}"
