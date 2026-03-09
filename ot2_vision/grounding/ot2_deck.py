"""OT-2 deck geometry: slot positions, dimensions, and coordinate lookup."""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class DeckSlot:
    """An OT-2 deck slot with its physical bounds."""

    slot_id: str  # "1" through "11", or "trash"
    x_origin: float  # mm, left edge
    y_origin: float  # mm, bottom edge
    width: float = 128.0  # mm (x dimension)
    height: float = 86.0  # mm (y dimension)

    def contains(self, x_mm: float, y_mm: float) -> bool:
        return self.x_origin <= x_mm <= self.x_origin + self.width and self.y_origin <= y_mm <= self.y_origin + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x_origin + self.width / 2, self.y_origin + self.height / 2)


# OT-2 deck slots from opentrons_shared_data cutout positions
OT2_SLOTS = [
    DeckSlot("1", 0.0, 0.0),
    DeckSlot("2", 132.5, 0.0),
    DeckSlot("3", 265.0, 0.0),
    DeckSlot("4", 0.0, 90.5),
    DeckSlot("5", 132.5, 90.5),
    DeckSlot("6", 265.0, 90.5),
    DeckSlot("7", 0.0, 181.0),
    DeckSlot("8", 132.5, 181.0),
    DeckSlot("9", 265.0, 181.0),
    DeckSlot("10", 0.0, 271.5),
    DeckSlot("11", 132.5, 271.5),
    DeckSlot("trash", 265.0, 271.5),
]

# OT-2 calibration reference points (mm) for ArUco marker placement
CALIBRATION_POINTS = {
    0: np.array([12.13, 9.0, 0.0]),  # Slot 1 bottom-left cross
    1: np.array([380.87, 9.0, 0.0]),  # Slot 3 bottom-right cross
    2: np.array([12.13, 258.0, 0.0]),  # Slot 7 top-left cross
    3: np.array([380.87, 258.0, 0.0]),  # Slot 9 top-right cross
}

# Overall deck dimensions (mm)
DECK_WIDTH = 393.0  # X dimension
DECK_DEPTH = 357.5  # Y dimension (slot 1 origin to slot 10 origin + slot height)


def find_slot(x_mm: float, y_mm: float) -> Optional[DeckSlot]:
    """Given a point in deck coordinates (mm), find which slot it falls in."""
    for slot in OT2_SLOTS:
        if slot.contains(x_mm, y_mm):
            return slot
    return None


def nearest_slot(x_mm: float, y_mm: float) -> DeckSlot:
    """Find the nearest slot to a point (for when point is slightly outside any slot)."""
    min_dist = float("inf")
    nearest = OT2_SLOTS[0]
    for slot in OT2_SLOTS:
        cx, cy = slot.center
        dist = np.sqrt((x_mm - cx) ** 2 + (y_mm - cy) ** 2)
        if dist < min_dist:
            min_dist = dist
            nearest = slot
    return nearest


def get_slot_by_id(slot_id: str) -> Optional[DeckSlot]:
    """Get a slot by its ID string."""
    for slot in OT2_SLOTS:
        if slot.slot_id == slot_id:
            return slot
    return None
