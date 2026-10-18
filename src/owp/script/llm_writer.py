"""LLM-backed script writer.

STUB. Q2.6 permits any model, balancing cost, engineering overhead and quality,
so the provider stays config (`OWP_LLM_PROVIDER`). Script generation is the
cheapest part of the pipeline either way - one long-context call per video
against a policy corpus - so model choice here is not where the $25/week budget
is won or lost (Q2.10).

The output is settled (Q2.1, answered 2026-10-17) and it has two steps, which
is why this class has two methods rather than one:

  1. **Mine the policy for processing types.** `practices` reads the corpus and
     returns `DataProcessing` values: what the company may do with the viewer's
     data, each with the verbatim policy text that establishes it. This step is
     about the document, so everything it returns is checkable against it.
  2. **Dramatize one of them.** `write` turns one processing type into a story
     the company's own CEO tells the viewer: what agreeing to this policy lets
     them do. This step is invention. The lines are written, not quoted, and
     asking for quotable dialogue would defeat the format.

Guardrails this writer must encode, in the prompt, in roughly this order of
importance:

  - **Capability, never conduct.** The subject is what the viewer's agreement
    *permits* - "I can match the photos you deleted to the ones you kept" - and
    never an assertion that the company did a particular thing to a particular
    viewer. The first is commentary on a published document; the second is a
    statement of fact about a named person, said by an animation of that
    person. This is the line that keeps the format defensible, and it is the
    one a model will cross on its own if the prompt lets it.
  - **Creepy by implication, from the document.** The story should unsettle by
    being true about what is allowed, not by escalating past it. "We may share
    this information with advertisers" licenses a great deal of quiet menace;
    it does not license "we sold your face to a stranger".
  - **Stay inside the cited processing.** A story that wanders to an adjacent,
    worse practice breaks the only link this pipeline can check.
  - Q2.8: name the company and use its logo; relevance should be obvious.
  - Q2.9 / Q4.6: tone is a hard constraint the optimizer may never trade off.
    The owner has set the register - creepy, first person - but not the
    ceiling, so `tone` stays an explicit parameter and review is the limit.

What is *not* required: a citation per beat. `verify_attribution` holds the
grounding rather than the dialogue, so beats are free prose, and an invented
quote is the only thing that will get a script rejected outright.
"""

from __future__ import annotations

from owp.models import DataProcessing, NarrativeFormat, PolicyCorpus, Script


class LlmScriptWriter:
    """Generates scripts from a policy corpus."""

    def __init__(
        self,
        *,
        provider: str = "gemini",
        model: str | None = None,
        tone: str = (
            "first person, calm, faintly proud: someone describing what they are "
            "allowed to do, not boasting about having done it"
        ),
    ) -> None:
        self.provider = provider
        self.model = model
        self.tone = tone

    def practices(self, corpus: PolicyCorpus, *, limit: int = 5) -> list[DataProcessing]:
        """Mine the corpus for processing types worth a video each (Q2.2).

        Returns the evidence with each one, not just a label: the next step
        writes fiction, so this is the last point at which what the video is
        about is still tied to the document.
        """
        raise NotImplementedError(
            "Processing extraction is not implemented. Requirements are settled (Q2.2)."
        )

    def write(
        self,
        corpus: PolicyCorpus,
        *,
        processing: DataProcessing,
        format: NarrativeFormat = NarrativeFormat.CEO_DIRECT_ADDRESS,
        target_seconds: float = 45.0,
    ) -> Script:
        raise NotImplementedError(
            "Script generation is not implemented. Requirements are now fully settled: "
            "Q2.1 was answered 2026-10-17 as the CEO addressing the viewer."
        )

    def _build_prompt(
        self, corpus: PolicyCorpus, processing: DataProcessing, format: NarrativeFormat
    ) -> str:
        """Assemble the generation prompt.

        Separate from `write` so prompts can be unit-tested and diffed: once the
        bandit attributes performance to prompt variants (Q4.4), a silently
        changed prompt invalidates the comparison. It is also where the
        guardrails above have to be stated explicitly, including the one a
        model will otherwise cross unprompted: capability, never conduct.
        """
        raise NotImplementedError
