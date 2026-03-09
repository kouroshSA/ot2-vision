"""Reusable OT-2 protocol primitives."""

WAVE_GOODBYE = '''
from opentrons import protocol_api

metadata = {"protocolName": "Wave Goodbye", "author": "ot2-vision"}
requirements = {"robotType": "OT-2", "apiLevel": "2.15"}

def run(protocol: protocol_api.ProtocolContext):
    plate_left = protocol.load_labware("corning_96_wellplate_360ul_flat", 4)
    plate_right = protocol.load_labware("corning_96_wellplate_360ul_flat", 6)

    pipette = protocol.load_instrument("p20_single_gen2", "right")

    # Flash lights twice at home position, then stay on
    protocol.set_rail_lights(True)
    protocol.delay(seconds=0.4)
    protocol.set_rail_lights(False)
    protocol.delay(seconds=0.4)
    protocol.set_rail_lights(True)
    protocol.delay(seconds=0.4)
    protocol.set_rail_lights(False)
    protocol.delay(seconds=0.4)
    protocol.set_rail_lights(True)

    # Wave! Fast sweeps staying high (150mm above wells)
    high = 150
    pipette.default_speed = 400

    pipette.move_to(plate_right["A1"].top(high))
    pipette.move_to(plate_left["A12"].top(high))
    pipette.move_to(plate_right["A1"].top(high))
    pipette.move_to(plate_left["A12"].top(high))
    pipette.move_to(plate_right["A1"].top(high))

    # Lights off, go home
    protocol.set_rail_lights(False)
    protocol.home()

    # One last flash at home
    protocol.set_rail_lights(True)
    protocol.delay(seconds=0.4)
    protocol.set_rail_lights(False)
    protocol.comment("Goodbye!")
'''
