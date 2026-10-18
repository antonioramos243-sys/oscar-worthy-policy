"""LLM-backed script writer.

STUB. Q2.6 permits any model, balancing cost, engineering overhead and quality,
so the provider stays config (`OWP_LLM_PROVIDER`). Script generation is the
cheapest part of the pipeline either way - one long-context call per video
against a policy corpus - so model choice here is not where the $25/week budget
is won or lost (Q2.10).

Guardrails this writer must encode:
  - Q2.8: name the company and use its logo; relevance should be obvious.
  - Q2.9: optimize for engaging, shareable videos, but Q4.6 makes tone a hard
    constraint the optimizer may never trade off. The doc does not say where
    the tone line sits, so `tone` is an explicit parameter rather than a
    hardcoded prompt, and its default is the conservative reading.
  - Q2.7: citations optional; do not misrepresent the policy.
"""

from __future__ import annotations

from owp.models import NarrativeFormat, PolicyCorpus, Script


class LlmScriptWriter:
    """Generates scripts from a policy corpus."""

    def __init__(
        self,
        *,
        provider: str = "gemini",
        model: str | None = None,
        tone: str = "factual, dry, unsettling by implication rather than assertion",
    ) -> None:
        self.provider = provider
        self.model = model
        self.tone = tone

    def practices(self, corpus: PolicyCorpus, *, limit: int = 5) -> list[str]:
        raise NotImplementedError(
            "Practice extraction is not implemented. Requirements are settled (Q2.2)."
        )

    def write(
        self,
        corpus: PolicyCorpus,
        *,
        practice: str,
        format: NarrativeFormat = NarrativeFormat.WHAT_THEY_KNOW,
        target_seconds: float = 45.0,
    ) -> Script:
        raise NotImplementedError(
            "Script generation is not implemented. Requirements are settled apart from Q2.1 "
            "(which narrative formats are in scope), which is still unanswered."
        )

    def _build_prompt(self, corpus: PolicyCorpus, practice: str, format: NarrativeFormat) -> str:
        """Assemble the generation prompt.

        Separate from `write` so prompts can be unit-tested and diffed: once the
        bandit attributes performance to prompt variants (Q4.4), a silently
        changed prompt invalidates the comparison.
        """
        raise NotImplementedError
