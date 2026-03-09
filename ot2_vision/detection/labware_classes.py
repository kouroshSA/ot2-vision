"""Labware class definitions for YOLOv8 detection."""

# Class ID -> (display_name, opentrons_load_name)
LABWARE_CLASSES: dict[int, tuple[str, str]] = {
    0: ("96-well plate", "corning_96_wellplate_360ul_flat"),
    1: ("96-well PCR plate", "opentrons_96_wellplate_200ul_pcr_full_skirt"),
    2: ("384-well plate", "corning_384_wellplate_112ul_flat"),
    3: ("300ul tip rack", "opentrons_96_tiprack_300ul"),
    4: ("1000ul tip rack", "opentrons_96_tiprack_1000ul"),
    5: ("12-row reservoir", "nest_12_reservoir_15ml"),
    6: ("1-well reservoir", "nest_1_reservoir_195ml"),
    7: ("24-tube rack", "opentrons_24_tuberack_nest_1.5ml_snapcap"),
    8: ("deep well plate", "nest_96_wellplate_2ml_deep"),
}


def get_display_name(class_id: int) -> str:
    """Get the human-readable display name for a class ID."""
    if class_id in LABWARE_CLASSES:
        return LABWARE_CLASSES[class_id][0]
    return f"unknown (class {class_id})"


def get_opentrons_name(class_id: int) -> str:
    """Get the Opentrons load name for a class ID."""
    if class_id in LABWARE_CLASSES:
        return LABWARE_CLASSES[class_id][1]
    return "unknown_labware"


# YOLOv8 dataset.yaml template for training
DATASET_YAML = """
path: {data_root}
train: images/train
val: images/val

names:
  0: 96-well-plate
  1: 96-well-pcr-plate
  2: 384-well-plate
  3: 300ul-tip-rack
  4: 1000ul-tip-rack
  5: 12-row-reservoir
  6: 1-well-reservoir
  7: 24-tube-rack
  8: deep-well-plate
"""
