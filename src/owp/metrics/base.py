"""Interface for pulling engagement data."""

from __future__ import annotations

from typing import Protocol

from owp.models import MetricsWindow, PostMetrics, ScheduledPost


class MetricsSource(Protocol):
    """Reads engagement for posts that have gone live."""

    def pull(self, post: ScheduledPost, window: MetricsWindow) -> PostMetrics:
        """Fetch metrics for one post at one observation window.

        Requires `post.instagram_url`, which only exists once the post is
        confirmed live - and how the system learns that is open (Q3.8).
        """
        ...
