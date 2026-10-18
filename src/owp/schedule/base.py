"""Interfaces for assigning posting slots and notifying the phone."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from owp.models import ScheduledPost, Video


class Scheduler(Protocol):
    """Assigns a posting slot to a finished video."""

    def schedule(self, video: Video, target_slug: str) -> ScheduledPost:
        """Place `video` in the next free slot.

        Cadence and whether slots are fixed or optimizer-chosen are open
        (Q3.1), as is whether an approval queue sits in front of scheduling
        (Q3.7).
        """
        ...

    def due(self, now: datetime) -> list[ScheduledPost]:
        """Posts whose slot has arrived and which have not been notified yet."""
        ...


class Notifier(Protocol):
    """Delivers the 'your video is ready' notification.

    This is the system's only outbound action: posting itself is manual, from
    Antonio's phone.
    """

    def notify(self, post: ScheduledPost) -> None:
        """Send a notification carrying a link to the video.

        The channel is open (Q3.2) and so is what the link opens (Q3.3) - a
        direct download, a signed Cloud Storage URL, or a small web page
        carrying the video, caption and hashtags together.
        """
        ...
