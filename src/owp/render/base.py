"""Interface for video rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from owp.cast import Cast
from owp.models import CaptionTrack, Script, Video, Voiceover

REEL_WIDTH = 1080
REEL_HEIGHT = 1920


class Renderer(Protocol):
    """Produces a finished vertical video.

    Two implementations are scaffolded because Q2.4 (animation with characters
    consistent across videos) and Q2.10 ($25/week) pull in opposite directions;
    see docs/requirements-decisions.md. Both take the same `Cast` so character
    identity comes from one place either way.
    """

    def render(
        self,
        script: Script,
        voiceover: Voiceover,
        captions: CaptionTrack,
        cast: Cast,
        *,
        out_dir: Path,
    ) -> Video:
        """Assemble a 1080x1920 video and report what it cost to make."""
        ...
