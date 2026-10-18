"""The pipeline's own guard rails, exercised with fake stages."""

from __future__ import annotations

from pathlib import Path

import pytest

from owp.models import CaptionTrack, Script, Video, Voiceover
from owp.pipeline import Pipeline


class _FakeRenderer:
    def __init__(self) -> None:
        self.calls = 0

    def render(
        self,
        script: Script,
        voiceover: Voiceover | None,
        captions: CaptionTrack,
        *,
        out_dir: Path,
    ) -> Video:
        self.calls += 1
        self.last_captions = captions
        return Video(path=out_dir / "out.mp4", duration_s=30.0)


def _pipeline(renderer: _FakeRenderer, tmp_path: Path) -> Pipeline:
    return Pipeline(
        fetcher=None,  # type: ignore[arg-type]
        writer=None,  # type: ignore[arg-type]
        renderer=renderer,
        scheduler=None,  # type: ignore[arg-type]
        notifier=None,  # type: ignore[arg-type]
        tts=None,
        out_dir=tmp_path,
    )


def test_refuses_to_render_unreviewed_script(script: Script, tmp_path: Path) -> None:
    renderer = _FakeRenderer()
    with pytest.raises(ValueError, match="not been reviewed"):
        _pipeline(renderer, tmp_path).produce(script)
    assert renderer.calls == 0


def test_renders_reviewed_script(script: Script, tmp_path: Path) -> None:
    script.reviewed = True
    renderer = _FakeRenderer()
    video = _pipeline(renderer, tmp_path).produce(script)
    assert renderer.calls == 1
    assert video.duration_s == 30.0


def test_captions_empty_without_tts(script: Script, tmp_path: Path) -> None:
    # Captions-only treatments still need the renderer to receive a track.
    script.reviewed = True
    renderer = _FakeRenderer()
    _pipeline(renderer, tmp_path).produce(script)
    assert renderer.last_captions.cues == []
