"""Wiring for the end-to-end pipeline.

The stages are injected rather than constructed here, so the undecided ones
(visual style, TTS, notification channel) can be swapped without touching the
orchestration, and so tests can run the whole flow with fakes.

The flow is: target -> snapshot -> script -> [verify] -> voiceover -> captions
-> video -> scheduled post -> notification -> metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from owp.acquisition.base import PolicyFetcher
from owp.captions.chunker import cues_from_word_timings
from owp.models import (
    CaptionTrack,
    NarrativeFormat,
    PolicySnapshot,
    ScheduledPost,
    Script,
    Target,
    Video,
)
from owp.render.base import Renderer
from owp.schedule.base import Notifier, Scheduler
from owp.script.base import ScriptWriter
from owp.script.verify import verify_citations
from owp.voice.base import TtsProvider


@dataclass
class Pipeline:
    """Runs a target through to a scheduled, notified post."""

    fetcher: PolicyFetcher
    writer: ScriptWriter
    renderer: Renderer
    scheduler: Scheduler
    notifier: Notifier
    tts: TtsProvider | None = None
    out_dir: Path = Path("data/renders")

    def acquire(self, target: Target) -> list[PolicySnapshot]:
        """Fetch every in-scope policy for one target."""
        return self.fetcher.fetch(target)

    def draft(
        self,
        snapshot: PolicySnapshot,
        *,
        format: NarrativeFormat,
        target_seconds: float = 45.0,
    ) -> Script:
        """Write a script and reject it if any quote is not in the policy.

        Verification runs here, not inside the writer, so a different writer
        cannot skip the accuracy gate.
        """
        script = self.writer.write(snapshot, format=format, target_seconds=target_seconds)
        verify_citations(script, snapshot)
        return script

    def produce(self, script: Script) -> Video:
        """Narrate, caption and render an approved script.

        Raises:
            ValueError: if the script has not been reviewed. Review is assumed
                mandatory before anything is rendered or scheduled (Q2.7).
        """
        if not script.reviewed:
            raise ValueError(
                f"Script for {script.target_slug} has not been reviewed; "
                "refusing to render an unreviewed script."
            )

        self.out_dir.mkdir(parents=True, exist_ok=True)
        voiceover = self.tts.synthesize(script, out_dir=self.out_dir) if self.tts else None
        cues = cues_from_word_timings(voiceover.word_timings) if voiceover else []
        captions = CaptionTrack(cues=cues)
        return self.renderer.render(script, voiceover, captions, out_dir=self.out_dir)

    def enqueue(self, video: Video, target_slug: str) -> ScheduledPost:
        """Give a finished video a posting slot."""
        return self.scheduler.schedule(video, target_slug)

    def notify_due(self, now: object) -> list[ScheduledPost]:
        """Notify every post whose slot has arrived.

        Returns the posts that were notified, so a caller can record state.
        """
        due = self.scheduler.due(now)  # type: ignore[arg-type]
        for post in due:
            self.notifier.notify(post)
        return due
