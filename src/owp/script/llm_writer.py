"""LLM-backed script writer.

STUB, and provider-agnostic on purpose: the platform is GCP, which points at
Gemini, but whether third-party models are acceptable is open (Q2.6). The
provider is selected by OWP_LLM_PROVIDER so that choice stays a config change.

Tone guardrails (Q2.9) and whether videos may name companies and show their
logos and UI (Q2.8) both belong in the prompt this class builds, so neither
should be hardcoded until they are decided.
"""

from __future__ import annotations

from owp.models import NarrativeFormat, PolicySnapshot, Script
from owp.script.base import ScriptWriter


class LlmScriptWriter(ScriptWriter):
    """Generates a script, then requires every factual beat to carry a citation."""

    def __init__(self, *, provider: str = "gemini", model: str | None = None) -> None:
        self.provider = provider
        self.model = model

    def write(
        self,
        snapshot: PolicySnapshot,
        *,
        format: NarrativeFormat = NarrativeFormat.WHAT_THEY_KNOW,
        target_seconds: float = 45.0,
    ) -> Script:
        raise NotImplementedError(
            "Script generation is not implemented. Blocked on Q2.1 (which formats are in "
            "scope), Q2.6 (permitted models), Q2.8 (naming companies) and Q2.9 (tone limits)."
        )

    def _build_prompt(self, snapshot: PolicySnapshot, format: NarrativeFormat) -> str:
        """Assemble the generation prompt.

        Kept separate from `write` so prompts can be unit-tested and diffed as
        they change, which matters once engagement data starts attributing
        performance to prompt variants (Q4.4).
        """
        raise NotImplementedError
