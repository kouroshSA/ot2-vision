"""Tests for protocol validator."""

from ot2_vision.protocol.validator import ProtocolValidator

VALID_PROTOCOL = '''
from opentrons import protocol_api

metadata = {
    'protocolName': 'Test Protocol',
    'author': 'OT2Vision',
    'description': 'Test',
}

requirements = {
    'robotType': 'OT-2',
    'apiLevel': '2.15',
}

def run(protocol: protocol_api.ProtocolContext):
    tip_rack = protocol.load_labware('opentrons_96_tiprack_300ul', 10)
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1)
    pipette = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tip_rack])
    pipette.transfer(10, plate['A1'], plate['B1'], new_tip='always')
'''

INVALID_SYNTAX = '''
def run(protocol):
    x = (
'''

MISSING_ELEMENTS = '''
def do_something():
    pass
'''


def test_valid_protocol_passes_syntax():
    ok, msg = ProtocolValidator.check_syntax(VALID_PROTOCOL)
    assert ok


def test_invalid_syntax_fails():
    ok, msg = ProtocolValidator.check_syntax(INVALID_SYNTAX)
    assert not ok
    assert "Syntax error" in msg


def test_valid_protocol_has_required_elements():
    ok, issues = ProtocolValidator.check_required_elements(VALID_PROTOCOL)
    assert ok
    assert len(issues) == 0


def test_missing_elements_detected():
    ok, issues = ProtocolValidator.check_required_elements(MISSING_ELEMENTS)
    assert not ok
    assert len(issues) > 0


def test_validate_combines_checks():
    ok, msg = ProtocolValidator.validate(VALID_PROTOCOL)
    assert ok

    ok, msg = ProtocolValidator.validate(INVALID_SYNTAX)
    assert not ok
    assert "Syntax error" in msg

    ok, msg = ProtocolValidator.validate(MISSING_ELEMENTS)
    assert not ok
