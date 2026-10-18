"""LLM-backed script writer.

STUB. Q2.6 permits any model, balancing cost, engineering overhead and quality,
so the provider stays config (`OWP_LLM_PROVIDER`). Script generation is the
cheapest part of the pipeline either way - one long-context call per video
against a policy corpus - so model choice here is not where the $25/week budget
is won or lost (Q2.10).

The shape of the output is settled (Q2.1, answered 2026-10-17): the covered
company's own CEO, speaking to the viewer, explaining what agreeing to their
privacy policy lets the company do with the viewer's data. So the writer casts
one speaker - `Cast.for_target` - and writes first person to second person.

Guardrails this writer must encode:
  - **Every beat carries a citation.** Not optional any more. The speaker is a
    real, named person, so an uncited claim is a quotation attributed to
    someone who never said it. `verify_attribution` rejects the script before
    anything renders, so an uncited beat is wasted generation, not a risk.
  - **Only what the policy permits, in the policy's own terms.** The subject is
    what agreeing *allows*, which is what the document actually establishes.
    "They will sell your face" is not in any of these policies; "we may share
    this information with advertisers" is.
  - Q2.8: name the company and use its logo; relevance should be obvious.
  - Q2.9: optimize for engaging, shareable videos, but Q4.6 makes tone a hard
    constraint the optimizer may never trade off. The doc does not say where
    the tone line sits, so `tone` is an explicit parameter rather than a
    hardcoded prompt, and its default is the conservative reading - which
    matters more now that the words are in a real person's mouth.
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
        format: NarrativeFormat = NarrativeFormat.CEO_DIRECT_ADDRESS,
        target_seconds: float = 45.0,
    ) -> Script:
        raise NotImplementedError(
            "Script generation is not implemented. Requirements are now fully settled: "
            "Q2.1 was answered 2026-10-17 as the CEO addressing the viewer."
        )

    def _build_prompt(self, corpus: PolicyCorpus, practice: str, format: NarrativeFormat) -> str:
        """Assemble the generation prompt.

        Separate from `write` so prompts can be unit-tested and diffed: once the
        bandit attributes performance to prompt variants (Q4.4), a silently
        changed prompt invalidates the comparison. It is also where the
        guardrails above have to be stated explicitly, including the one the
        model will otherwise break: every beat needs a verbatim quote from the
        corpus, because the speaker is a real person.
        """
        raise NotImplementedError
