"""Google Cloud Text-to-Speech provider.

STUB. Chosen as the default because the platform is already GCP, but whether
narration is synthetic at all is open (Q2.5) - the alternatives are Antonio's
own voice, which makes this class unused, or captions with no narration, which
makes the whole voice stage optional.

Implementation note for whoever picks this up: wrap each beat in an SSML
`<mark>` and request timepoints, then map them onto word timings. That is the
cheap path to accurate captions; forced alignment is the fallback, not the plan.
"""

from __future__ import annotations

from pathlib import Path

from owp.models import Script, Voiceover
from owp.voice.base import TtsProvider


class CloudTtsProvider(TtsProvider):
    """Synthesizes narration with Google Cloud TTS."""

    def __init__(self, *, voice_id: str = "en-US-Studio-O", speaking_rate: float = 1.0) -> None:
        self.voice_id = voice_id
        self.speaking_rate = speaking_rate

    def synthesize(self, script: Script, *, out_dir: Path) -> Voiceover:
        raise NotImplementedError(
            "TTS is not implemented. Blocked on Q2.5 (synthetic voice vs Antonio's own voice "
            "vs captions only)."
        )
