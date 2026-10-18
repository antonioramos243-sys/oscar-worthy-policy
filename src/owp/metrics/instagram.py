"""Instagram Graph API metrics.

STUB, and blocked on something outside the code: Graph API insights require a
Business or Creator account, which is unconfirmed (Q4.1). If the account is
personal, this component cannot be built as specified at all and the fallback
is manual entry of a few numbers per post.

No optimizer module is scaffolded. Q4.2 has not named a single primary
objective, and an optimizer without one would just encode a guess. Collect
metrics first; add the optimizer when the objective exists.
"""

from __future__ import annotations

from owp.metrics.base import MetricsSource
from owp.models import MetricsWindow, PostMetrics, ScheduledPost


class InstagramGraphMetrics(MetricsSource):
    """Pulls insights for a post via the Instagram Graph API."""

    def __init__(self, *, ig_user_id: str, access_token: str) -> None:
        self.ig_user_id = ig_user_id
        self._access_token = access_token

    def pull(self, post: ScheduledPost, window: MetricsWindow) -> PostMetrics:
        raise NotImplementedError(
            "Metrics collection is not implemented. Blocked on Q4.1 (Business/Creator "
            "account) and Q4.3 (which pull windows)."
        )
