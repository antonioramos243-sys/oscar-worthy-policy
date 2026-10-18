"""Domain model shared by every pipeline stage.

These types are the contract between stages. A stage takes the previous
stage's output and returns its own; nothing reaches across.

Decisions are referenced inline as (Qn.m) and recorded in
docs/requirements-decisions.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import ClassVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, HttpUrl

# Q3.9: Eastern time, no posting before 09:00 or after 22:00.
POSTING_TZ = ZoneInfo("America/New_York")
QUIET_HOURS_END = 9
QUIET_HOURS_START = 22


class Category(StrEnum):
    """The four target groups that make up the 40-policy set."""

    SOCIAL = "social"       # 10 most popular social media platforms
    DATING = "dating"       # 10 most popular dating apps
    AI = "ai"               # 5 most popular AI applications
    TOP_APP = "top_app"     # 15 most popular websites or applications


class PolicyKind(StrEnum):
    """The policy documents merged into one corpus per target (Q1.4)."""

    MAIN_PRIVACY = "main_privacy"
    COOKIE = "cookie"
    REGIONAL = "regional"
    PRODUCT_SPECIFIC = "product_specific"


class Target(BaseModel):
    """A company/app we intend to cover, before its policy is fetched.

    Ranked by monthly active users in the US (Q1.2). Cross-category duplicates
    are dropped and replaced by the next-ranked entry (Q1.1), so a slug appears
    at most once across the whole set.
    """

    slug: str = Field(description="Stable id, e.g. 'instagram'.")
    company: str
    category: Category
    product: str | None = Field(
        default=None,
        description="The specific ranked product whose policy applies (Q1.4).",
    )
    rank: int | None = Field(default=None, description="Rank within its category.")
    policy_urls: dict[PolicyKind, HttpUrl] = Field(default_factory=dict)


class PolicySource(BaseModel):
    """One document that was merged into a corpus."""

    kind: PolicyKind
    url: HttpUrl
    extracted_manually: bool = Field(
        default=False,
        description="True when automated extraction failed and text was pasted in (Q1.7).",
    )


class PolicyCorpus(BaseModel):
    """The merged US policy text for one target.

    Q1.4 asks for the main policy, cookie policy and any others combined into
    one document, so a video can tell a cohesive story about how a platform
    uses data. Cleaned text only - raw HTML is not retained (Q1.8) - and one
    snapshot per target, with no version history (Q1.6).
    """

    target_slug: str
    fetched_at: datetime
    text: str = Field(description="Cleaned, merged policy text. English only (Q1.9).")
    sources: list[PolicySource]
    content_hash: str = Field(description="sha256 of the merged cleaned text.")

    @property
    def merged_kinds(self) -> list[PolicyKind]:
        return [s.kind for s in self.sources]


class VisualStyle(StrEnum):
    """Variations within the animation direction set by Q2.4.

    Shared contract: the optimizer varies it (Q4.4) and the renderer uses it to
    pick a background plate set, so it lives here rather than in either.
    """

    FLAT = "flat"
    NOIR = "noir"
    CORPORATE = "corporate"


class NarrativeFormat(StrEnum):
    """Candidate video formats.

    Q2.1 is the one question with no answer in the doc, so all five remain in
    scope and the optimizer treats format as a variable to explore (Q4.4).
    """

    EXPLAINER = "explainer"
    SKIT = "skit"
    WHAT_THEY_KNOW = "what_they_know"
    COMPARISON = "comparison"
    HORROR_STORY = "horror_story"


class Citation(BaseModel):
    """Policy text supporting a claim.

    Optional: Q2.7 does not require per-claim citations, because every video
    gets a personal review. Where the writer does supply one, it is checked
    verbatim against the corpus - cheap insurance against the one failure that
    review is worst at catching, a confident paraphrase of something the policy
    never said.
    """

    quote: str = Field(description="Verbatim excerpt from the policy corpus.")
    section: str | None = None
    char_start: int | None = None
    char_end: int | None = None


class ScriptBeat(BaseModel):
    """One narrated line, optionally with the evidence behind it."""

    text: str = Field(description="What the voiceover says.")
    citation: Citation | None = None
    character: str | None = Field(
        default=None, description="Speaking character's cast id (Q2.4)."
    )
    visual_note: str | None = Field(default=None, description="Direction for the render stage.")


class Script(BaseModel):
    """A script for one video, covering one data practice.

    Q2.2: several videos per policy, each focused on a specific practice, so a
    script names the practice it covers rather than the whole policy.
    """

    target_slug: str
    content_hash: str = Field(description="Hash of the corpus this was written from.")
    practice: str = Field(description="The single data practice this video is about (Q2.2).")
    format: NarrativeFormat
    hook: str = Field(description="First 1-2 seconds; the scroll-stopper.")
    beats: list[ScriptBeat]
    estimated_seconds: float = Field(description="Target 30-90s (Q2.3).")

    @property
    def narration(self) -> str:
        """The script as one block of text, for TTS."""
        return " ".join(beat.text for beat in self.beats)


class WordTiming(BaseModel):
    """When a single word is spoken, used to time captions without re-aligning audio."""

    word: str
    start_s: float
    end_s: float


class Voiceover(BaseModel):
    """Synthesized narration. Q2.5: synthetic voice."""

    audio_path: Path
    duration_s: float
    voice_id: str
    word_timings: list[WordTiming] = Field(default_factory=list)


class CaptionCue(BaseModel):
    """One on-screen caption chunk."""

    text: str
    start_s: float
    end_s: float


class CaptionTrack(BaseModel):
    """Burned-in captions. Social video is watched muted."""

    cues: list[CaptionCue]


class Video(BaseModel):
    """A finished render, ready to be scheduled."""

    path: Path
    duration_s: float
    width: int = 1080
    height: int = 1920
    cover_frame_path: Path | None = None
    generation_cost_usd: float | None = Field(
        default=None,
        description="Billed cost of this render, including discarded takes. "
        "Tracked because the weekly cap is $25 (Q2.10).",
    )


class QualityScore(BaseModel):
    """Antonio's perceived quality score, applied when a video is ready (Q2.6).

    Multi-dimensional on purpose: 'the animation looked wrong' and 'the story
    did not land' call for different fixes, and the optimizer needs to know
    which dimension a variant hurt.

    Scores are 1-5. A video below `threshold` on `overall` is not posted.
    """

    animation_quality: int = Field(ge=1, le=5)
    character_consistency: int = Field(ge=1, le=5)
    narrative_consistency: int = Field(ge=1, le=5)
    storyline_quality: int = Field(ge=1, le=5)
    notes: str | None = None

    DIMENSIONS: ClassVar[tuple[str, ...]] = (
        "animation_quality",
        "character_consistency",
        "narrative_consistency",
        "storyline_quality",
    )

    @property
    def overall(self) -> float:
        """Unweighted mean of the dimensions.

        Unweighted until there is engagement data to say which dimension
        predicts performance; weighting it now would be a guess.
        """
        total = sum(int(getattr(self, d)) for d in self.DIMENSIONS)
        return total / len(self.DIMENSIONS)

    def passes(self, threshold: float = 3.5) -> bool:
        return self.overall >= threshold


class PostState(StrEnum):
    """Lifecycle of a video on its way to Instagram.

    Q3.7: there is no pre-approval queue - every finished video goes straight
    to the schedule. Review happens when Antonio is notified, which is where
    REJECTED comes from. The system never posts; it can only learn that a post
    happened, by Antonio pasting the URL back (Q3.8).
    """

    RENDERED = "rendered"
    SCHEDULED = "scheduled"
    NOTIFIED = "notified"
    POSTED = "posted"
    ROLLED = "rolled"        # Slot missed; moved to the next one (Q3.6)
    REJECTED = "rejected"    # Quality score below threshold (Q2.6)


class ScheduledPost(BaseModel):
    """A video assigned a posting slot, plus the copy to paste alongside it.

    Caption, hashtags and cover frame are generated by the system (Q3.4), so
    the notification page carries everything needed to post in one go (Q3.3).
    """

    target_slug: str
    practice: str
    video: Video
    scheduled_for: datetime = Field(description="Eastern time, 09:00-22:00 (Q3.9).")
    caption: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    state: PostState = PostState.RENDERED
    quality_score: QualityScore | None = None
    notified_at: datetime | None = None
    posted_at: datetime | None = None
    instagram_url: HttpUrl | None = None
    roll_count: int = Field(default=0, description="How many slots this has been rolled through.")


class MetricsWindow(StrEnum):
    """Observation windows after posting (Q4.3)."""

    H1 = "1h"
    H3 = "3h"
    H9 = "9h"
    H24 = "24h"
    D7 = "7d"


#: Q4.3 lists the windows but not which one scores a variant. 24h is the
#: default: long enough for a Reel's first distribution wave, short enough that
#: the bandit is not waiting a week per observation. D7 is kept for reporting.
SCORING_WINDOW = MetricsWindow.H24


class PostMetrics(BaseModel):
    """Engagement for one post at one observation window.

    Q4.2 names the objective as informing people about poor privacy practices.
    That is a mission, not a metric; `reach` is the closest measurable proxy
    (people who saw it), with `shares` as the amplification term. See
    docs/requirements-decisions.md.
    """

    target_slug: str
    instagram_url: HttpUrl
    window: MetricsWindow
    pulled_at: datetime
    views: int | None = None
    reach: int | None = None
    watch_time_s: float | None = None
    shares: int | None = None
    saves: int | None = None
    follows: int | None = None
    comments: int | None = Field(
        default=None,
        description="Count only. Comment text is not collected (Q4.8, Q4.10).",
    )
