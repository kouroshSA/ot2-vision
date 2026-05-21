"""Tests for the vision scene analyzer (mocked Claude API, no real API calls)."""


def test_parse_json_from_code_block():
    """Parser should extract JSON from ```json ... ``` code blocks."""
    from ot2_vision.vision.scene_analyzer import SceneAnalyzer

    analyzer = SceneAnalyzer.__new__(SceneAnalyzer)

    response = '''Here is the analysis:
```json
{"labware": [{"slot": 1, "type": "96-well plate", "load_name": "corning_96_wellplate_360ul_flat", "confidence": "high"}], "notes": "test"}
```'''
    result = analyzer._parse_response(response)
    assert len(result["labware"]) == 1
    assert result["labware"][0]["slot"] == 1
    assert result["labware"][0]["load_name"] == "corning_96_wellplate_360ul_flat"


def test_parse_raw_json():
    """Parser should handle raw JSON without code blocks."""
    from ot2_vision.vision.scene_analyzer import SceneAnalyzer

    analyzer = SceneAnalyzer.__new__(SceneAnalyzer)

    response = '{"labware": [], "notes": "empty deck"}'
    result = analyzer._parse_response(response)
    assert result["labware"] == []
    assert result["notes"] == "empty deck"


def test_build_scene_text_format():
    """build_scene_text should produce <deck_state> XML with correct spatial info."""
    from ot2_vision.vision.scene_analyzer import SceneAnalyzer

    analyzer = SceneAnalyzer.__new__(SceneAnalyzer)

    analysis = {
        "labware": [
            {"slot": 1, "type": "96-well plate", "load_name": "corning_96_wellplate_360ul_flat", "confidence": "high"},
            {"slot": 10, "type": "20uL tip rack", "load_name": "opentrons_96_tiprack_20ul", "confidence": "medium"},
        ],
        "notes": "Clear plates in front slots",
    }

    text = analyzer.build_scene_text(analysis)
    assert "<deck_state>" in text
    assert "Slot 1" in text
    assert "Slot 10" in text
    assert "corning_96_wellplate_360ul_flat" in text
    assert "opentrons_96_tiprack_20ul" in text
    assert "front/near" in text  # slot 1
    assert "back/far" in text  # slot 10


def test_build_scene_text_empty():
    """build_scene_text should handle empty labware list."""
    from ot2_vision.vision.scene_analyzer import SceneAnalyzer

    analyzer = SceneAnalyzer.__new__(SceneAnalyzer)

    analysis = {"labware": [], "notes": ""}
    text = analyzer.build_scene_text(analysis)
    assert "No labware detected" in text
