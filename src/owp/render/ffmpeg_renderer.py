"""ffmpeg-based renderer.

STUB, and the stage most exposed to an undecided requirement: the visual style
is wide open (Q2.4) and the options differ so much that they are not one
implementation. AI-generated footage (Veo), animation, a stock-footage montage,
an avatar presenter, and text-over-b-roll each imply a different pipeline;
only the last is a pure ffmpeg job.

ffmpeg is not installed on this machine - see README for setup.
"""

from __future__ import annotations

from pathlib import Path

from owp.models import CaptionTrack, Script, Video, Voiceover
from owp.render.base import Renderer

REEL_WIDTH = 1080
REEL_HEIGHT = 1920


class FfmpegRenderer(Renderer):
    """Burns captions over a visual bed and muxes in narration."""

    def __init__(self, *, ffmpeg_bin: str = "ffmpeg") -> None:
        self.ffmpeg_bin = ffmpeg_bin

    def render(
        self,
        script: Script,
        voiceover: Voiceover | None,
        captions: CaptionTrack,
        *,
        out_dir: Path,
    ) -> Video:
        raise NotImplementedError(
            "Rendering is not implemented. Blocked on Q2.4 (visual style), which determines "
            "whether this is an ffmpeg job at all."
        )
