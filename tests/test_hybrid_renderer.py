from __future__ import annotations

from pathlib import Path

import pytest

from owp.cast import Cast, Character
from owp.models import Script, VisualStyle, Voiceover
from owp.render.hybrid_renderer import HybridRenderer
from owp.render.plates import NoPlatesForStyle, Plate, PlateLibrary


def cast() -> Cast:
    return Cast(
        characters=[
            Character(id="narrator", name="The Narrator", role="r", appearance="a"),
            Character(id="user", name="The User", role="r", appearance="a"),
        ]
    )


def library(style: VisualStyle = VisualStyle.FLAT, *, generated: bool = True) -> PlateLibrary:
    return PlateLibrary(
        [
            Plate(id="p1", style=style, prompt="x", path="p1.mp4" if generated else None),
            Plate(id="p2", style=style, prompt="x", path="p2.mp4" if generated else None),
        ]
    )


def voiceover(duration_s: float) -> Voiceover:
    return Voiceover(audio_path=Path("vo.wav"), duration_s=duration_s, voice_id="t")


def test_plan_covers_the_voiceover_duration(script: Script) -> None:
    plan = HybridRenderer(library=library()).plan(script, voiceover(30.0), cast())
    assert sum(p.seconds for p in plan.plates) >= 30.0
    assert plan.duration_s == 30.0


def test_plan_uses_voiceover_duration_not_the_script_estimate(script: Script) -> None:
    # script.estimated_seconds is 30.0; the real narration ran long.
    plan = HybridRenderer(library=library()).plan(script, voiceover(48.0), cast())
    assert plan.duration_s == 48.0
    assert sum(p.seconds for p in plan.plates) >= 48.0


def test_plan_resolves_characters_in_first_appearance_order(script: Script) -> None:
    plan = HybridRenderer(library=library()).plan(script, voiceover(16.0), cast())
    assert [c.id for c in plan.characters] == ["narrator", "user"]


def test_plan_deduplicates_repeated_characters(script: Script) -> None:
    for beat in script.beats:
        beat.character = "narrator"
    plan = HybridRenderer(library=library()).plan(script, voiceover(16.0), cast())
    assert [c.id for c in plan.characters] == ["narrator"]


def test_plan_marginal_cost_is_zero(script: Script) -> None:
    # Plates are reused, so a render books no new per-second spend.
    plan = HybridRenderer(library=library()).plan(script, voiceover(60.0), cast())
    assert plan.marginal_cost_usd == 0.0


def test_plan_fails_when_the_style_has_no_generated_plates(script: Script) -> None:
    renderer = HybridRenderer(library=library(generated=False))
    with pytest.raises(NoPlatesForStyle):
        renderer.plan(script, voiceover(16.0), cast())


def test_plan_fails_on_an_unknown_character(script: Script) -> None:
    script.beats[0].character = "the-ceo"
    with pytest.raises(KeyError, match="the-ceo"):
        HybridRenderer(library=library()).plan(script, voiceover(16.0), cast())


def test_render_reports_the_resolved_plan_in_its_error(script: Script) -> None:
    renderer = HybridRenderer(library=library())
    with pytest.raises(NotImplementedError, match="plates"):
        renderer.render(script, voiceover(16.0), None, cast(), out_dir=Path("/tmp"))  # type: ignore[arg-type]
