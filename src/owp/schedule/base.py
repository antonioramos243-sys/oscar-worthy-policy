"""Interfaces for assigning posting slots and notifying the phone."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from owp.models import ScheduledPost, Video


class Scheduler(Protocol):
    """Assigns posting slots to finished videos.

    Q3.7: no approval queue - every finished video goes straight to the
    schedule. Review happens at notification time, where the quality score is
    applied (Q2.6).
    """

    def schedule(self, video: Video, target_slug: str, practice: str) -> ScheduledPost:
        """Place `video` in the next free slot."""
        ...

    def due(self, now: datetime) -> list[ScheduledPost]:
        """Posts whose slot has arrived and which have not been notified."""
        ...

    def roll(self, post: ScheduledPost, now: datetime) -> ScheduledPost:
        """Move a missed post to the next slot (Q3.6)."""
        ...


class Notifier(Protocol):
    """Delivers the 'your video is ready' notification.

    The system's only outbound action: posting is manual (Q3.8 - Antonio pastes
    the Instagram URL back afterwards).
    """

    def notify(self, post: ScheduledPost) -> None:
        """Send a notification linking to the review page for `post`."""
        ...
