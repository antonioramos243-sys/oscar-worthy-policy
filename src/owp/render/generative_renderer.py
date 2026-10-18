"""Generative video rendering (Veo-class models).

STUB, and the expensive path. Q2.6 permits any model subject to cost,
engineering overhead and quality, and Q2.4 asks for consistent characters - but
per-second billing collides with the $25/week cap (Q2.10):

    60s at Veo 3.1 Lite 720p  ~$3.00   4/wk = $12.00   fits
    60s at Veo 3.1 Lite 1080p ~$4.80   4/wk = $19.20   fits, little headroom
    60s at Veo 3.1 Fast       ~$12.00  4/wk = $48.00   over cap
    60s at Veo 3.1 Standard   ~$30.00  4/wk = $120.00  over cap

Discarded takes bill too, and Q2.6 introduces a quality score that may reject a
video, so the effective cost per *posted* video is higher than the table: at a
50% rejection rate even the Lite tier reaches ~$24/week.

Character consistency across separate generations is also the weak point of
these models, and `Cast.reference_images` is the lever - it is conditioning
input, not a guarantee.

Keep `usd_per_second` explicit and charge through owp.budget before generating.
"""

from __future__ import annotations

from pathlib import Path

from owp.cast import Cast
from owp.models import CaptionTrack, Script, Video, Voiceover

#: Veo 3.1 Lite at 720p - the only tier with real headroom under the weekly cap.
#: Verify against Google's own pricing page before relying on it.
DEFAULT_USD_PER_SECOND = 0.05


class GenerativeRenderer:
    """Generates footage with a hosted video model, then muxes narration and captions."""

    def __init__(
        self,
        *,
        model: str = "veo-3.1-lite",
        usd_per_second: float = DEFAULT_USD_PER_SECOND,
        resolution: str = "720p",
    ) -> None:
        self.model = model
        self.usd_per_second = usd_per_second
        self.resolution = resolution

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
            "Generative rendering is not implemented. Needs a decision on the quality/cost "
            "trade-off first: see the tier table above against the $25/week cap (Q2.10)."
        )
