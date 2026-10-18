"""Domain model shared by every pipeline stage.

These types are the contract between stages. A stage takes the previous
stage's output and returns its own; nothing reaches across.

Open requirements questions are referenced inline as (Qn.m) and tracked in
docs/requirements-open-questions.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl


class Category(StrEnum):
    """The four target groups that make up the 40-policy MVP set."""

    SOCIAL = "social"       # 10 most popular social media platforms
    DATING = "dating"       # 10 most popular dating apps
    AI = "ai"               # 5 most popular AI applications
    TOP_APP = "top_app"     # 15 most popular websites or applications


class Jurisdiction(StrEnum):
    """Which regional variant of a policy a snapshot represents (Q1.5)."""

    US = "us"
    EU = "eu"
    UNKNOWN = "unknown"


class PolicyKind(StrEnum):
    """Companies publish several policies; which are in scope is open (Q1.4)."""

    MAIN_PRIVACY = "main_privacy"
    COOKIE = "cookie"
    REGIONAL = "regional"
    PRODUCT_SPECIFIC = "product_specific"


class Target(BaseModel):
    """A company/app we intend to cover, before its policy is fetched.

    Ranking comes from a third-party popularity source (Sensor Tower or a
    hand-curated list). The measure and market are still open (Q1.2), as is
    how cross-category duplicates are handled (Q1.1).
    """

    slug: str = Field(description="Stable id, e.g. 'instagram'.")
    company: str
    category: Category
    rank: int | None = Field(default=None, description="Rank within its category.")
    policy_urls: dict[PolicyKind, HttpUrl] = Field(default_factory=dict)


class PolicySnapshot(BaseModel):
    """One fetch of one policy document at one point in time.

    Both raw HTML and cleaned text are retained, and snapshots are immutable
    and append-only, so change detection has something to diff against
    (Q1.6, Q1.8). `content_hash` is over `text`, not `raw_html`, so that
    markup churn does not read as a policy change.
    """

    target_slug: str
    kind: PolicyKind = PolicyKind.MAIN_PRIVACY
    jurisdiction: Jurisdiction = Jurisdiction.US
    source_url: HttpUrl
    fetched_at: datetime
    text: str
    raw_html: str | None = None
    content_hash: str = Field(description="sha256 of the cleaned text.")
    language: str = "en"
    extracted_manually: bool = Field(
        default=False,
        description="True when automated extraction failed and text was uploaded by hand (Q1.7).",
    )


class NarrativeFormat(StrEnum):
    """Candidate video formats. Which are in scope is open (Q2.1)."""

    EXPLAINER = "explainer"
    SKIT = "skit"
    WHAT_THEY_KNOW = "what_they_know"
    COMPARISON = "comparison"
    HORROR_STORY = "horror_story"


class Citation(BaseModel):
    """Ties one factual claim back to the policy text that supports it.

    The accuracy bar is not settled (Q2.7), but the model assumes the strict
    reading: every claim carries a verbatim quote and its location, so a
    reviewer can check a script without re-reading the policy.
    """

    quote: str = Field(description="Verbatim excerpt from the policy snapshot.")
    section: str | None = Field(default=None, description="Heading or clause, if identifiable.")
    char_start: int | None = None
    char_end: int | None = None


class ScriptBeat(BaseModel):
    """One narrated line plus the evidence behind it."""

    text: str = Field(description="What the voiceover says.")
    citation: Citation | None = Field(
        default=None,
        description="None is allowed only for non-factual framing lines (hooks, transitions).",
    )
    visual_note: str | None = Field(default=None, description="Direction for the render stage.")


class Script(BaseModel):
    """A full video script derived from one policy snapshot."""

    target_slug: str
    content_hash: str = Field(description="Hash of the snapshot this was written from.")
    format: NarrativeFormat
    hook: str = Field(description="First 1-2 seconds; the scroll-stopper.")
    beats: list[ScriptBeat]
    estimated_seconds: float = Field(description="Target length is open (Q2.3); Reels run 15-90s.")
    reviewed: bool = Field(
        default=False,
        description="Personal review before scheduling - assumed mandatory (Q2.7).",
    )

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
    """Synthesized narration for a script.

    Whether narration is synthetic, Antonio's own voice, or dropped in favour
    of captions alone is open (Q2.5).
    """

    audio_path: Path
    duration_s: float
    voice_id: str
    word_timings: list[WordTiming] = Field(
        default_factory=list,
        description="Empty when the provider cannot report timings; captions then need alignment.",
    )


class CaptionCue(BaseModel):
    """One on-screen caption chunk."""

    text: str
    start_s: float
    end_s: float


class CaptionTrack(BaseModel):
    """Burned-in captions. Assumed mandatory, since social video is watched muted."""

    cues: list[CaptionCue]


class Video(BaseModel):
    """A finished render, ready for review and scheduling."""

    path: Path
    duration_s: float
    width: int = 1080
    height: int = 1920
    cover_frame_path: Path | None = Field(
        default=None, description="Cover frame to pick in the Instagram composer (Q3.4)."
    )


class PostState(StrEnum):
    """Lifecycle of a video on its way to Instagram.

    Posting is manual from Antonio's phone, so the system can only ever
    believe a post happened; it cannot perform it. How it learns is open (Q3.8).
    """

    RENDERED = "rendered"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    NOTIFIED = "notified"
    POSTED = "posted"
    MISSED = "missed"


class ScheduledPost(BaseModel):
    """A video assigned a posting slot, plus the copy to paste alongside it."""

    target_slug: str
    video: Video
    scheduled_for: datetime = Field(description="Time zone and quiet hours are open (Q3.9).")
    caption: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    state: PostState = PostState.RENDERED
    notified_at: datetime | None = None
    posted_at: datetime | None = None
    instagram_url: HttpUrl | None = None


class MetricsWindow(StrEnum):
    """When metrics were pulled relative to posting (Q4.3)."""

    H1 = "1h"
    H24 = "24h"
    D7 = "7d"


class PostMetrics(BaseModel):
    """Engagement for one post at one observation window.

    Which metric is the single primary objective is open (Q4.2); the optimizer
    should not be written until that is decided.
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
    comments: int | None = None
