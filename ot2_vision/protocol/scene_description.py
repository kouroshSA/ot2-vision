"""Build structured text scene descriptions from grounded detections."""

from ..grounding.spatial_resolver import GroundedObject, get_spatial_description


def build_scene_description(objects: list[GroundedObject]) -> str:
    """
    Build a structured text description of the current OT-2 deck state
    from detected and grounded objects. This becomes part of the Claude prompt context.
    """
    if not objects:
        return "<deck_state>\nNo labware detected on the deck.\n</deck_state>"

    lines = ["<deck_state>", "The following labware was detected on the OT-2 deck:"]

    for i, obj in enumerate(objects, 1):
        lines.append(
            f"  {i}. {obj.detection.class_name} "
            f"(confidence: {obj.detection.confidence:.0%}) "
            f"in Slot {obj.slot.slot_id} "
            f"[deck position: x={obj.deck_position[0]:.0f}mm, y={obj.deck_position[1]:.0f}mm]"
        )
        lines.append(f"     Opentrons load name: {obj.labware_name}")
        lines.append(f"     Spatial: {get_spatial_description(obj.deck_position)}")

    lines.append("</deck_state>")
    return "\n".join(lines)


def build_mock_scene(slot_labware: dict[str, tuple[str, str]]) -> str:
    """
    Build a mock scene description from a slot -> (class_name, load_name) mapping.
    Useful for testing without a camera.

    Example: {"1": ("96-well plate", "corning_96_wellplate_360ul_flat"),
              "5": ("300ul tip rack", "opentrons_96_tiprack_300ul")}
    """
    from ..grounding.ot2_deck import get_slot_by_id

    lines = ["<deck_state>", "The following labware was detected on the OT-2 deck:"]

    for i, (slot_id, (class_name, load_name)) in enumerate(slot_labware.items(), 1):
        slot = get_slot_by_id(slot_id)
        if slot is None:
            continue
        cx, cy = slot.center
        lines.append(
            f"  {i}. {class_name} (confidence: 95%) "
            f"in Slot {slot_id} "
            f"[deck position: x={cx:.0f}mm, y={cy:.0f}mm]"
        )
        lines.append(f"     Opentrons load name: {load_name}")
        lines.append(f"     Spatial: {get_spatial_description((cx, cy, 0.0))}")

    lines.append("</deck_state>")
    return "\n".join(lines)
