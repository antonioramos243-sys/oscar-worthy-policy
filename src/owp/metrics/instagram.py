"""Instagram Graph API metrics.

STUB. Q4.1 confirms a Creator account, so Graph API insights are available.

Q4.3 sets the pull schedule at 1h, 3h, 9h, 24h and 7d. It does not say which
window scores a variant; `owp.models.SCORING_WINDOW` picks 24h, long enough to
capture a Reel's first distribution wave and short enough that the bandit is
not blocked a week per observation. 7d is kept for reporting.

Q4.8/Q4.10: comment counts only - no comment text is collected, and engagement
data is retained indefinitely.
"""

from __future__ import annotations

from owp.models import MetricsWindow, PostMetrics, ScheduledPost

#: Q4.3, in hours after posting.
PULL_SCHEDULE_HOURS: tuple[float, ...] = (1, 3, 9, 24, 168)


class InstagramGraphMetrics:
    """Pulls insights for a post via the Instagram Graph API."""

    def __init__(self, *, ig_user_id: str, access_token: str) -> None:
        self.ig_user_id = ig_user_id
        self._access_token = access_token

    def pull(self, post: ScheduledPost, window: MetricsWindow) -> PostMetrics:
        raise NotImplementedError(
            "Metrics collection is not implemented. Requirements are settled (Q4.1, Q4.3)."
        )
