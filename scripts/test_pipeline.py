#!/usr/bin/env python3
"""Test the full pipeline in demo mode (no camera/OT-2 needed)."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from ot2_vision.config import get_config
from ot2_vision.protocol.generator import ProtocolGenerator
from ot2_vision.protocol.scene_description import build_mock_scene
from ot2_vision.protocol.validator import ProtocolValidator


def main():
    config = get_config()

    # Mock scene: two 96-well plates and a tip rack
    slot_labware = {
        "1": ("96-well plate", "corning_96_wellplate_360ul_flat"),
        "3": ("96-well plate", "corning_96_wellplate_360ul_flat"),
        "10": ("300ul tip rack", "opentrons_96_tiprack_300ul"),
    }
    scene_desc = build_mock_scene(slot_labware)

    print("=== Mock Scene ===")
    print(scene_desc)
    print()

    instruction = "Transfer 10 microliters from well A1 of the near-left plate to well B4 of the near-right plate"
    print(f"=== Instruction ===\n{instruction}\n")

    print("=== Generating Protocol ===")
    generator = ProtocolGenerator(api_key=config.anthropic_api_key)
    code = generator.generate_from_scene_text(instruction, scene_desc)

    print("=== Generated Protocol ===")
    print(code)
    print()

    print("=== Validation ===")
    is_valid, msg = ProtocolValidator.validate(code)
    print(f"Valid: {is_valid} — {msg}")

    # Try simulation if opentrons is available
    print("\n=== Simulation ===")
    sim_ok, sim_output = ProtocolValidator.simulate(code)
    if sim_ok:
        print("Simulation PASSED")
    else:
        print(f"Simulation output:\n{sim_output}")


if __name__ == "__main__":
    main()
