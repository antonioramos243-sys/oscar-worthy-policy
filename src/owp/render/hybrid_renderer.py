"""Hybrid renderer: drawn characters composited over generated background plates.

The chosen approach (Q2.4 + Q2.10). It splits the problem along the line where
each technique is strong:

  - Backgrounds come from a generated plate library, built once and reused
    (`owp.render.plates`). Variety is cheap and the cost is one-off.
  - Characters are drawn assets from `owp.cast`, composited on top. They are the
    same files in every video, so consistency across videos is structural
    rather than something a model has to maintain.

Steady-state marginal cost is TTS plus one LLM call, about $0.16 a video, which
is why this fits a firm $25/week cap once the library exists.

`plan` is implemented - plate and character selection is logic worth testing on
its own. `render` shells out to ffmpeg and is stubbed; ffmpeg is not installed
on this machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from owp.cast import Cast, Character
from owp.models import CaptionTrack, Script, Video, VisualStyle, Voiceover
from owp.render.plates import Plate, PlateLibrary


@dataclass(frozen=True)
class RenderPlan:
    """Everything the ffmpeg stage needs, resolved up front.

    Separated from execution so a render can be inspected - and its cost
    confirmed as zero - before anything is invoked.
    """

    duration_s: float
    plates: list[Plate]
    characters: list[Character]
    style: VisualStyle
    marginal_cost_usd: float = 0.0

    @property
    def plate_ids(self) -> list[str]:
        return [p.id for p in self.plates]


class HybridRenderer:
    """Composites the drawn cast over reused background plates."""

    def __init__(
        self,
        *,
        library: PlateLibrary | None = None,
        ffmpeg_bin: str = "ffmpeg",
    ) -> None:
        self.library = library or PlateLibrary.load()
        self.ffmpeg_bin = ffmpeg_bin

    def plan(
        self,
        script: Script,
        voiceover: Voiceover,
        cast: Cast,
        *,
        style: VisualStyle = VisualStyle.FLAT,
    ) -> RenderPlan:
        """Resolve plates and characters for one video.

        Duration comes from the voiceover rather than `script.estimated_seconds`:
        the narration is what the captions and cuts are timed against, and the
        estimate is only ever an estimate.

        Raises:
            NoPlatesForStyle: if the library has no generated plates for `style`.
            KeyError: if a beat names a character absent from the cast.
        """
        plates = self.library.cover(style, voiceover.duration_s)
        ids = [b.character for b in script.beats if b.character is not None]
        # dict.fromkeys keeps first-appearance order while de-duplicating.
        characters = [cast.get(cid) for cid in dict.fromkeys(ids)]
        return RenderPlan(
            duration_s=voiceover.duration_s,
            plates=plates,
            characters=characters,
            style=style,
            marginal_cost_usd=0.0,
        )

    def render(
        self,
        script: Script,
        voiceover: Voiceover,
        captions: CaptionTrack,
        cast: Cast,
        *,
        out_dir: Path,
    ) -> Video:
        plan = self.plan(script, voiceover, cast)
        raise NotImplementedError(
            f"Hybrid rendering is not implemented. The plan resolves "
            f"({len(plan.plates)} plates, {len(plan.characters)} characters, "
            f"{plan.duration_s:.1f}s), but execution needs ffmpeg and the drawn "
            f"character assets - cast.json has placeholder appearances and no asset_dir."
        )
