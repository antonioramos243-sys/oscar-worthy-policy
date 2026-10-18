"""The recurring character cast: the CEOs of the companies being covered.

Q2.4 asks for animation with characters consistent across videos, which is a
state problem before it is a rendering problem: whatever draws a frame needs the
same cast definition every time, or episode 12 quietly stops looking like
episode 1.

**Decided 2026-10-17: the cast is the CEO of each covered company**, speaking to
camera (Q2.1). That changes what this file has to carry.

A character is now usually a real, identifiable person, so two fields stop being
optional. `real_person` is what the citation gate in `owp.script.verify` keys
off: a line put in a real person's mouth has to be backed by text the policy
actually contains, because an invented one is not a factual slip about a company
but a false statement about a named individual. And `verified_on` / `source`
record who held the job and when it was checked, since a video in which last
quarter's CEO explains this quarter's policy is wrong in a way that review is
poor at catching - the face looks right.

One CEO covers every target their company publishes a policy for, so the cast is
smaller than the target list and the same drawn person recurs across all of a
company's videos, which is exactly the consistency Q2.4 wants.

Asset-based animation uses the `asset_dir` sprites directly; generative video
uses `appearance` as prompt text plus `reference_images` for conditioning.
Either way the source of truth is this file, not a prompt someone retypes.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

CAST_FILE = Path(__file__).with_name("cast.json")


class Character(BaseModel):
    """One recurring character."""

    id: str = Field(description="Stable id referenced by ScriptBeat.character.")
    name: str
    role: str = Field(description="What this character is for, narratively.")
    appearance: str = Field(
        description="Canonical description; prompt text for generative video. For a real "
        "person this is a brief for a caricature and must say so: a likeness that could "
        "pass as footage is the one thing this project must not produce."
    )
    real_person: bool = Field(
        default=False,
        description="True when the character depicts a real, identifiable person. Gates "
        "the citation requirement in owp.script.verify.",
    )
    company: str | None = Field(
        default=None, description="The company whose policy this person is answerable for."
    )
    title: str | None = Field(default=None, description="Their role at that company.")
    target_slugs: list[str] = Field(
        default_factory=list,
        description="Targets whose policy this company publishes. One CEO can cover "
        "several, which is why this is a list and not a single slug.",
    )
    verified_on: date | None = Field(
        default=None, description="When this person was last confirmed to hold the job."
    )
    source: str | None = Field(default=None, description="Where that was confirmed.")
    voice_id: str | None = Field(
        default=None,
        description="TTS voice, so a character sounds consistent too. A plainly "
        "synthetic voice, never a clone of the real person's.",
    )
    asset_dir: str | None = Field(default=None, description="Sprite/rig directory for assets.")
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

    def for_target(self, target_slug: str) -> Character:
        """The character who speaks in `target_slug`'s videos.

        Raises:
            KeyError: when no cast member covers the target. Fetching a policy
                is no use if there is nobody to deliver it.
        """
        for character in self.characters:
            if target_slug in character.target_slugs:
                return character
        raise KeyError(
            f"no cast member covers target {target_slug!r}; add the CEO of the company "
            f"that publishes its policy to {CAST_FILE.name}"
        )

    def real_people(self) -> list[Character]:
        """Characters depicting real people, which is most of them."""
        return [c for c in self.characters if c.real_person]

    def missing_for(self, target_slugs: Iterable[str]) -> list[str]:
        """Targets with no cast member yet, sorted.

        Reported rather than raised, like `CuratedTargetSource.shortfall`: the
        target list is still a placeholder, so an incomplete cast is the
        expected state and should be visible without failing every command.
        """
        covered = {slug for c in self.characters for slug in c.target_slugs}
        return sorted(set(target_slugs) - covered)

    def ids(self) -> set[str]:
        return {c.id for c in self.characters}
