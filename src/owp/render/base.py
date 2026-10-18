"""Interface for video rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from owp.models import CaptionTrack, Script, Video, Voiceover


class Renderer(Protocol):
    """Produces a finished vertical video."""

    def render(
        self,
        script: Script,
        voiceover: Voiceover | None,
        captions: CaptionTrack,
        *,
        out_dir: Path,
    ) -> Video:
        """Assemble a 1080x1920 video.

        `voiceover` is optional so a captions-only treatment stays possible
        without a second renderer (Q2.5).
        """
        ...
