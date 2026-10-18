"""Component 2b: narration."""

from owp.voice.base import TtsProvider
from owp.voice.gcp_tts import CloudTtsProvider

__all__ = ["TtsProvider", "CloudTtsProvider"]
