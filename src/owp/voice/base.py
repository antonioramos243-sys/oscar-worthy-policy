"""Interface for text-to-speech."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from owp.models import Script, Voiceover


class TtsProvider(Protocol):
    """Synthesizes narration audio for a script.

    Implementations should populate `Voiceover.word_timings` wherever the
    backend can report them. Google Cloud TTS can, via SSML `<mark>` timepoints,
    which lets the captions stage skip forced alignment entirely.
    """

    def synthesize(self, script: Script, *, out_dir: Path) -> Voiceover:
        """Render `script.narration` to an audio file under `out_dir`."""
        ...
