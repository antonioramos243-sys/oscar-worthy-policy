"""Asset-based 2D animation: a fixed cast of drawn characters, animated locally.

STUB, but the recommended default. Both of the hardest constraints point here:

  - Q2.4 wants characters consistent across videos. With sprites and rigs
    checked into the repo, consistency is not a modelling problem - episode 12
    uses the same artwork as episode 1 because it is the same file.
  - Q2.10 caps spend at $25/week. Rendering locally has no per-second billing,
    so marginal cost is TTS plus one LLM call, around $0.16 a video. The cap
    stops being the binding constraint.

The cost is up front and human: somebody has to draw the cast and build the
rigs. After that, volume is nearly free.

ffmpeg is not installed on this machine - see README.
"""

from __future__ import annotations

from pathlib import Path

from owp.cast import Cast
from owp.models import CaptionTrack, Script, Video, Voiceover


class AssetAnimationRenderer:
    """Animates the checked-in cast against the narration, then burns captions."""

    def __init__(self, *, ffmpeg_bin: str = "ffmpeg") -> None:
        self.ffmpeg_bin = ffmpeg_bin

    def render(
        self,
        script: Script,
        voiceover: Voiceover,
        captions: CaptionTrack,
        cast: Cast,
        *,
        out_dir: Path,
    ) -> Video:
        raise NotImplementedError(
            "Asset-based rendering is not implemented. Blocked on artwork, not on a "
            "decision: the cast in cast.json has placeholder appearances and no asset_dir."
        )
