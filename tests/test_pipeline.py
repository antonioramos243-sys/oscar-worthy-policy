"""The pipeline's gates, exercised with fake stages."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from owp.budget import BudgetExceeded, Charge
from owp.cast import Cast
from owp.models import (
    CaptionTrack,
    PostState,
    QualityScore,
    ScheduledPost,
    Script,
    Video,
    Voiceover,
    WordTiming,
)
from owp.pipeline import Pipeline

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


class _FakeTts:
    def synthesize(self, script: Script, *, out_dir: Path) -> Voiceover:
        return Voiceover(
            audio_path=out_dir / "vo.wav",
            duration_s=2.0,
            voice_id="test",
            word_timings=[
                WordTiming(word="they", start_s=0.0, end_s=0.3),
                WordTiming(word="know", start_s=0.3, end_s=0.6),
            ],
        )


class _FakeRenderer:
    def __init__(self, cost: float | None = None) -> None:
        self.calls = 0
        self.cost = cost
        self.last_captions: CaptionTrack | None = None

    def render(self, script, voiceover, captions, cast, *, out_dir):  # noqa: ANN001, ANN201
        self.calls += 1
        self.last_captions = captions
        return Video(
            path=out_dir / "out.mp4", duration_s=30.0, generation_cost_usd=self.cost
        )


def _pipeline(renderer: _FakeRenderer, tmp_path: Path, charges=None) -> Pipeline:
    return Pipeline(
        fetcher=None,
        writer=None,
        renderer=renderer,
        tts=_FakeTts(),
        scheduler=None,
        notifier=None,
        cast=Cast.load(),
        charges=list(charges or []),
        out_dir=tmp_path,
    )


def test_renders_without_a_prior_approval_step(script: Script, tmp_path: Path) -> None:
    # Q3.7: every finished video goes straight to the queue; no approval gate.
    renderer = _FakeRenderer()
    video = _pipeline(renderer, tmp_path).produce(script, now=NOW)
    assert renderer.calls == 1
    assert video.duration_s == 30.0


def test_captions_are_built_from_tts_timings(script: Script, tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    _pipeline(renderer, tmp_path).produce(script, now=NOW)
    assert renderer.last_captions is not None
    assert [c.text for c in renderer.last_captions.cues] == ["they know"]


def test_budget_gate_blocks_a_render_over_the_weekly_cap(
    script: Script, tmp_path: Path
) -> None:
    renderer = _FakeRenderer()
    pipeline = _pipeline(renderer, tmp_path, charges=[Charge(at=NOW, usd=24.0)])
    with pytest.raises(BudgetExceeded):
        pipeline.produce(script, now=NOW, estimated_cost_usd=5.0)
    assert renderer.calls == 0, "must not spend before raising"


def test_billed_render_is_recorded_against_the_week(script: Script, tmp_path: Path) -> None:
    pipeline = _pipeline(_FakeRenderer(cost=3.0), tmp_path)
    pipeline.produce(script, now=NOW, estimated_cost_usd=3.0)
    assert pipeline.spent_this_week(NOW) == 3.0


def test_free_render_records_no_charge(script: Script, tmp_path: Path) -> None:
    pipeline = _pipeline(_FakeRenderer(cost=None), tmp_path)
    pipeline.produce(script, now=NOW)
    assert pipeline.spent_this_week(NOW) == 0.0


def _post(tmp_path: Path) -> ScheduledPost:
    return ScheduledPost(
        target_slug="instagram",
        practice="watch-time tracking",
        video=Video(path=tmp_path / "o.mp4", duration_s=30.0),
        scheduled_for=NOW,
    )


def test_low_quality_score_rejects_the_post(tmp_path: Path) -> None:
    pipeline = _pipeline(_FakeRenderer(), tmp_path)
    score = QualityScore(
        animation_quality=2,
        character_consistency=2,
        narrative_consistency=2,
        storyline_quality=2,
    )
    post = pipeline.record_review(_post(tmp_path), score)
    assert post.state is PostState.REJECTED


def test_passing_quality_score_leaves_the_post_alone(tmp_path: Path) -> None:
    pipeline = _pipeline(_FakeRenderer(), tmp_path)
    score = QualityScore(
        animation_quality=5,
        character_consistency=4,
        narrative_consistency=4,
        storyline_quality=4,
    )
    post = pipeline.record_review(_post(tmp_path), score)
    assert post.state is not PostState.REJECTED
    assert post.quality_score is not None
