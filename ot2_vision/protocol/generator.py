"""Protocol generation using Claude API with visual scene context."""

import re
from pathlib import Path

from ..config import get_config
from ..grounding.spatial_resolver import GroundedObject
from .prompt_templates import USER_PROMPT_TEMPLATE, VISION_SYSTEM_PROMPT
from .scene_description import build_scene_description


class ProtocolGenerator:
    """Generate OT-2 protocols using Claude API with visual scene context."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from anthropic import Anthropic

        config = get_config()
        self.client = Anthropic(api_key=api_key or config.anthropic_api_key)
        self.model = model or config.anthropic_model_codegen
        self.max_tokens = 4096
        self.reference_docs = self._load_reference_docs()

    def _load_reference_docs(self) -> str:
        """Load key reference docs from OpentronsAI server storage."""
        config = get_config()
        docs_path = Path(config.opentrons_docs_path)
        if not docs_path.exists():
            return ""

        docs = []
        key_files = [
            "deck_layout.md",
            "full-examples.md",
            "casual_examples.md",
            "standard-loadname-info.md",
        ]
        for fname in key_files:
            fpath = docs_path / fname
            if fpath.exists():
                content = fpath.read_text()
                docs.append(f"<reference_doc name='{fname}'>\n{content}\n</reference_doc>")

        return "\n".join(docs)

    def generate(self, user_instruction: str, grounded_objects: list[GroundedObject]) -> str:
        """
        Generate an OT-2 protocol from user instruction + visual scene.

        Returns Python protocol code as a string.
        """
        scene_desc = build_scene_description(grounded_objects)

        system = VISION_SYSTEM_PROMPT.format(
            scene_description=scene_desc,
            reference_docs=self.reference_docs,
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            scene_description=scene_desc,
            user_instruction=user_instruction,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.0,
        )

        raw_text = response.content[0].text
        return self._extract_protocol(raw_text)

    def generate_from_scene_text(self, user_instruction: str, scene_description: str) -> str:
        """Generate protocol from pre-built scene description text (for demo/mock mode)."""
        system = VISION_SYSTEM_PROMPT.format(
            scene_description=scene_description,
            reference_docs=self.reference_docs,
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            scene_description=scene_description,
            user_instruction=user_instruction,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.0,
        )

        raw_text = response.content[0].text
        return self._extract_protocol(raw_text)

    def _extract_protocol(self, response_text: str) -> str:
        """Extract Python code from Claude's response."""
        match = re.search(r"```python\s*\n(.*?)```", response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: return entire response
        return response_text.strip()
