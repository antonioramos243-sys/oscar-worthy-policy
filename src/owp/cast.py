"""The recurring character cast.

Q2.4 asks for animation with characters consistent across videos, which is a
state problem before it is a rendering problem: whatever draws a frame needs the
same cast definition every time, or episode 12 quietly stops looking like
episode 1.

So the cast is checked into the repo as data, with a stable id per character.
Asset-based animation uses the `asset_dir` sprites directly; generative video
uses `appearance` as prompt text plus `reference_images` for conditioning. Either
way the source of truth is this file, not a prompt someone retypes.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

CAST_FILE = Path(__file__).with_name("cast.json")


class Character(BaseModel):
    """One recurring character."""

    id: str = Field(description="Stable id referenced by ScriptBeat.character.")
    name: str
    role: str = Field(description="What this character is for, narratively.")
    appearance: str = Field(
        description="Canonical description; prompt text for generative video."
    )
    voice_id: str | None = Field(
        default=None, description="TTS voice, so a character sounds consistent too."
    )
    asset_dir: str | None = Field(
        default=None, description="Sprite/rig directory for asset-based animation."
    )
    reference_images: list[str] = Field(default_factory=list)


class Cast(BaseModel):
    """The full cast, loaded from cast.json."""

    characters: list[Character]

    @classmethod
    def load(cls, path: Path = CAST_FILE) -> Cast:
        return cls.model_validate({"characters": json.loads(path.read_text())})

    def get(self, character_id: str) -> Character:
        for character in self.characters:
            if character.id == character_id:
                return character
        raise KeyError(f"unknown character {character_id!r}; add it to {CAST_FILE.name}")

    def ids(self) -> set[str]:
        return {c.id for c in self.characters}
