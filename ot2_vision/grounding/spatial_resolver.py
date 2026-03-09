"""Resolve spatial references like 'far plate' or 'near-left tip rack' to grounded objects."""

from dataclasses import dataclass
from typing import Optional

from ..detection.detector import Detection
from .ot2_deck import DeckSlot


@dataclass
class GroundedObject:
    """A detected object grounded to a deck position."""

    detection: Detection
    slot: DeckSlot
    deck_position: tuple[float, float, float]  # (x_mm, y_mm, z_mm) in deck coords
    labware_name: str  # Opentrons load name

    @property
    def slot_id(self) -> str:
        return self.slot.slot_id


def resolve_spatial_reference(
    reference: str,
    objects: list[GroundedObject],
    labware_type: Optional[str] = None,
) -> Optional[GroundedObject]:
    """
    Resolve a spatial reference like "far plate" or "left tip rack".

    OT-2 deck orientation (from operator's perspective):
    - "near" / "front" / "close" = low Y (slots 1,2,3)
    - "far"  / "back"            = high Y (slots 10,11)
    - "left"                     = low X (slots 1,4,7,10)
    - "right"                    = high X (slots 3,6,9)
    """
    candidates = list(objects)

    # Filter by labware type if specified
    if labware_type:
        type_lower = labware_type.lower()
        candidates = [
            o
            for o in candidates
            if type_lower in o.labware_name.lower() or type_lower in o.detection.class_name.lower()
        ]

    if not candidates:
        return None

    ref = reference.lower().strip()

    # Sort by the primary spatial axis
    if "far" in ref or "back" in ref:
        candidates.sort(key=lambda o: o.deck_position[1], reverse=True)
    elif "near" in ref or "front" in ref or "close" in ref:
        candidates.sort(key=lambda o: o.deck_position[1])

    # Secondary sort by X axis if left/right specified
    if "left" in ref:
        candidates.sort(key=lambda o: o.deck_position[0])
    elif "right" in ref:
        candidates.sort(key=lambda o: o.deck_position[0], reverse=True)

    return candidates[0] if candidates else None


def get_spatial_description(deck_position: tuple[float, float, float]) -> str:
    """Return a human-readable spatial description for a deck position."""
    y = deck_position[1]
    x = deck_position[0]
    parts = []

    if y < 90:
        parts.append("front/near")
    elif y > 200:
        parts.append("back/far")
    else:
        parts.append("middle")

    if x < 130:
        parts.append("left")
    elif x > 260:
        parts.append("right")
    else:
        parts.append("center")

    return ", ".join(parts) + " side of deck"
