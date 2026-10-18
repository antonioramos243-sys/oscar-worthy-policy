"""Wiring for the end-to-end pipeline.

Stages are injected, so the two renderer options can be swapped and tests can
run the whole flow with fakes.

Flow: target -> corpus -> script -> [verify] -> voiceover -> captions -> video
-> scheduled post -> notification -> [review] -> posted -> metrics -> bandit.

Two gates live here rather than inside a stage, so no implementation can skip
them:
  - quote and cast verification, after drafting (Q2.7, Q2.4)
  - the weekly spend cap, before any billed render (Q2.10)

Note what is *not* a gate: there is no pre-approval step. Q3.7 sends every
finished video straight to the schedule, and the quality score is applied at
review time via `record_review`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from owp.acquisition.base import PolicyFetcher
from owp.budget import Charge, check_affordable
from owp.captions.chunker import cues_from_word_timings
from owp.cast import Cast
from owp.models import (
    CaptionTrack,
    DataProcessing,
    NarrativeFormat,
    PolicyCorpus,
    PostState,
    QualityScore,
    ScheduledPost,
    Script,
    Target,
    Video,
)
from owp.render.base import Renderer
from owp.schedule.base import Notifier, Scheduler
from owp.script.base import ScriptWriter
from owp.script.verify import verify_attribution, verify_cast, verify_quotes
from owp.voice.base import TtsProvider


@dataclass
class Pipeline:
    """Runs a target through to a notified post, and feeds results back."""

    fetcher: PolicyFetcher
    writer: ScriptWriter
    renderer: Renderer
    tts: TtsProvider
    scheduler: Scheduler
    notifier: Notifier
    cast: Cast = field(default_factory=Cast.load)
    charges: list[Charge] = field(default_factory=list)
    out_dir: Path = Path("data/renders")

    # -- component 1 ------------------------------------------------------
    def acquire(self, target: Target) -> PolicyCorpus:
        """Fetch and merge every in-scope policy for one target (Q1.4)."""
        return self.fetcher.fetch(target)
    # -- component 2 ------------------------------------------------------
    def draft(
        self,
        corpus: PolicyCorpus,
        *,
        processing: DataProcessing,
        format: NarrativeFormat,
        target_seconds: float = 60.0,
    ) -> Script:
        """Write a script, then check it against the corpus and the cast.

        Verification runs here, not in the writer, so swapping writers cannot
        drop it. Since the cast became real people (Q2.1), that includes the
        attribution gate: an uncited line in a CEO's mouth never reaches a
        renderer, whoever wrote it.
        """
        script = self.writer.write(
            corpus, processing=processing, format=format, target_seconds=target_seconds
        )
        verify_quotes(script, corpus)
        verify_cast(script, self.cast.ids())
        verify_attribution(script, self.cast)
        return script

    def produce(self, script: Script, *, now: datetime, estimated_cost_usd: float = 0.0) -> Video:
        """Narrate, caption and render a script.

        Args:
            script: The script to produce.
            now: Used to bucket the charge into the right week.
            estimated_cost_usd: Expected billed cost. Checked against the
                weekly cap *before* spending; pass 0.0 for a local renderer
                with no per-second billing.

        Raises:
            BudgetExceeded: if the render would breach the $25 weekly cap.
        """
        if estimated_cost_usd > 0:
            check_affordable(self.charges, now, estimated_cost_usd)

        self.out_dir.mkdir(parents=True, exist_ok=True)
        voiceover = self.tts.synthesize(script, out_dir=self.out_dir)
        captions = CaptionTrack(cues=cues_from_word_timings(voiceover.word_timings))
        video = self.renderer.render(
            script, voiceover, captions, self.cast, out_dir=self.out_dir
        )

        billed = video.generation_cost_usd
        if billed:
            self.charges.append(Charge(at=now, usd=billed, note=script.target_slug))
        return video

    # -- component 3 ------------------------------------------------------
    def enqueue(self, video: Video, script: Script) -> ScheduledPost:
        """Give a finished video a posting slot. No approval step (Q3.7)."""
        return self.scheduler.schedule(
            video, script.target_slug, script.practice
        )

    def notify_due(self, now: datetime) -> list[ScheduledPost]:
        """Notify every post whose slot has arrived, and mark it notified."""
        due = self.scheduler.due(now)
        for post in due:
            self.notifier.notify(post)
            post.state = PostState.NOTIFIED
            post.notified_at = now
        return due

    def record_review(
        self, post: ScheduledPost, score: QualityScore, *, threshold: float = 3.5
    ) -> ScheduledPost:
        """Apply the quality score Antonio assigns at review time (Q2.6).

        Below threshold the post is rejected rather than rolled: rolling a
        video that failed on quality would only re-offer the same video in a
        later slot.
        """
        post.quality_score = score
        if not score.passes(threshold):
            post.state = PostState.REJECTED
        return post

    # -- component 4 ------------------------------------------------------
    def spent_this_week(self, now: datetime) -> float:
        """Total billed in `now`'s ISO week (Q2.10)."""
        from owp.budget import spent_in_week

        return spent_in_week(self.charges, now)

    def add_charges(self, charges: Iterable[Charge]) -> None:
        """Load prior spend, e.g. on restart, so the weekly cap survives restarts."""
        self.charges.extend(charges)
