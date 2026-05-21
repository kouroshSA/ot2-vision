"""Analyze OT-2 deck images using Claude Vision API to identify labware and slot positions."""

import base64
import json
import logging
import re

from ..config import get_config

logger = logging.getLogger(__name__)

SCENE_ANALYSIS_PROMPT = """You are looking at an overhead camera image of an Opentrons OT-2 liquid handling robot deck.

The OT-2 deck has 11 numbered slots arranged in a 4-row by 3-column grid, plus a fixed trash bin.
From the operator's perspective (looking at the front of the robot):

    Slot 10  | Slot 11  | [Trash]     <- BACK (far from operator)
    Slot 7   | Slot 8   | Slot 9
    Slot 4   | Slot 5   | Slot 6
    Slot 1   | Slot 2   | Slot 3      <- FRONT (near operator)
    LEFT                  RIGHT

Each slot can hold one piece of labware. The slot numbers are engraved on the deck surface.

**Your task**: Analyze this image and identify ALL labware on the deck. For each piece, determine:
1. Which slot number it is in (1-11)
2. What type of labware it is
3. The correct Opentrons API load name from this list:
   - 96-well plate (clear, flat bottom): "corning_96_wellplate_360ul_flat"
   - 96-well PCR plate (low profile): "opentrons_96_wellplate_200ul_pcr_full_skirt"
   - 384-well plate: "corning_384_wellplate_112ul_flat"
   - 20uL tip rack: "opentrons_96_tiprack_20ul"
   - 300uL tip rack: "opentrons_96_tiprack_300ul"
   - 1000uL tip rack: "opentrons_96_tiprack_1000ul"
   - 12-row reservoir: "nest_12_reservoir_15ml"
   - 1-well reservoir: "nest_1_reservoir_195ml"
   - 24-tube rack: "opentrons_24_tuberack_nest_1.5ml_snapcap"
   - Deep well plate: "nest_96_wellplate_2ml_deep"

**Important context**:
- The robot has a P20 Single Gen2 pipette on the RIGHT mount (handles 1-20 uL)
- This pipette uses "opentrons_96_tiprack_20ul" tip racks
- Clear/transparent plates with a grid of small round wells are typically 96-well plates
- Black/dark rectangular labware with a grid of cylindrical tips is typically a tip rack
- Opentrons tip racks have evenly-spaced cylindrical tips in an 8x12 grid

Respond with ONLY a JSON object in this exact format:
```json
{
  "labware": [
    {"slot": 1, "type": "96-well plate", "load_name": "corning_96_wellplate_360ul_flat", "confidence": "high"}
  ],
  "notes": "Brief description of what you see and any uncertainties"
}
```

Be conservative: if unsure about a labware type, say so in notes and set confidence to "low".
"""


class SceneAnalyzer:
    """Analyze OT-2 deck images using Claude Vision API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from anthropic import Anthropic

        config = get_config()
        self.client = Anthropic(api_key=api_key or config.anthropic_api_key)
        self.model = model or config.anthropic_model_vision

    def analyze_image(self, image_jpeg_bytes: bytes) -> dict:
        """Send a JPEG image to Claude Vision and get structured labware identification."""
        image_b64 = base64.b64encode(image_jpeg_bytes).decode("utf-8")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": SCENE_ANALYSIS_PROMPT,
                        },
                    ],
                }
            ],
            temperature=0.0,
        )

        raw_text = response.content[0].text
        logger.debug(f"Claude Vision raw response:\n{raw_text}")
        return self._parse_response(raw_text)

    def analyze_image_file(self, image_path: str) -> dict:
        """Analyze an image from a file path."""
        import cv2
        import numpy as np

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Convert to JPEG if not already
        if not image_path.lower().endswith((".jpg", ".jpeg")):
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            _, jpeg_buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            image_bytes = jpeg_buf.tobytes()

        return self.analyze_image(image_bytes)

    def _parse_response(self, response_text: str) -> dict:
        """Extract JSON from Claude's response."""
        # Try code block first
        match = re.search(r"```json\s*\n(.*?)```", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

        # Try raw JSON
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse scene analysis response: {response_text[:200]}")
        return {"labware": [], "notes": f"Failed to parse response: {response_text[:200]}"}

    def build_scene_text(self, analysis: dict) -> str:
        """Convert analysis dict into <deck_state> XML format for ProtocolGenerator."""
        from ..grounding.ot2_deck import get_slot_by_id
        from ..grounding.spatial_resolver import get_spatial_description

        labware_list = analysis.get("labware", [])

        if not labware_list:
            return "<deck_state>\nNo labware detected on the deck.\n</deck_state>"

        lines = ["<deck_state>", "The following labware was detected on the OT-2 deck:"]

        for i, item in enumerate(labware_list, 1):
            slot_id = str(item["slot"])
            slot = get_slot_by_id(slot_id)
            if slot is None:
                continue

            cx, cy = slot.center
            confidence = item.get("confidence", "medium")
            conf_pct = {"high": "95%", "medium": "75%", "low": "50%"}.get(confidence, "75%")

            lines.append(
                f"  {i}. {item['type']} (confidence: {conf_pct}) "
                f"in Slot {slot_id} "
                f"[deck position: x={cx:.0f}mm, y={cy:.0f}mm]"
            )
            lines.append(f"     Opentrons load name: {item['load_name']}")
            lines.append(f"     Spatial: {get_spatial_description((cx, cy, 0.0))}")

        lines.append("</deck_state>")

        notes = analysis.get("notes", "")
        if notes:
            lines.append(f"\n<vision_notes>{notes}</vision_notes>")

        return "\n".join(lines)
