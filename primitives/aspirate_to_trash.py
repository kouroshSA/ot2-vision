"""Pick a tip, aspirate a small volume, throw the tip away (with liquid still in it).

Useful for removing a known volume from a well without depositing it anywhere on
the deck. The aspirated liquid goes to the trash bin along with the tip.

Edit the constants below to adapt to your run.
"""

from opentrons import protocol_api

# ---- edit for your run ----
TIP_WELL = "A6"             # which well of the tip rack to pick up from
SOURCE_WELL = "A1"          # which well of the source plate to aspirate from
VOLUME_UL = 5               # how much to aspirate (and trash) in microliters
TIP_RACK_SLOT = 7           # deck slot of the tip rack
SOURCE_PLATE_SLOT = 1       # deck slot of the source plate
# ----------------------------

metadata = {"protocolName": "Aspirate to trash + wave", "author": "ot2-vision"}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}


def run(protocol: protocol_api.ProtocolContext):
    source_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", SOURCE_PLATE_SLOT)
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", TIP_RACK_SLOT)
    pipette = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])

    protocol.set_rail_lights(True)

    protocol.comment(f"Picking up tip from slot {TIP_RACK_SLOT} well {TIP_WELL}...")
    pipette.pick_up_tip(tip_rack[TIP_WELL])

    protocol.comment(f"Aspirating {VOLUME_UL} uL from slot {SOURCE_PLATE_SLOT} well {SOURCE_WELL}...")
    pipette.aspirate(VOLUME_UL, source_plate[SOURCE_WELL])

    protocol.comment("Dropping tip in trash (with liquid)...")
    pipette.drop_tip()

    protocol.comment("Wave goodbye!")
    for _ in range(4):
        protocol.set_rail_lights(False)
        protocol.delay(seconds=0.25)
        protocol.set_rail_lights(True)
        protocol.delay(seconds=0.25)

    pipette.move_to(source_plate["A1"].top(z=80))
    pipette.move_to(source_plate["A12"].top(z=80))
    pipette.move_to(source_plate["A1"].top(z=80))

    protocol.home()
    protocol.set_rail_lights(False)
