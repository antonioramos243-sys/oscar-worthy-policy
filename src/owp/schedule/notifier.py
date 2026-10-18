"""Notification delivery.

STUB. Q3.2 lists six candidate channels (Firebase push to a companion app,
SMS, email, Telegram, Slack, Google Chat) and they are not interchangeable in
effort: push needs an app built and shipped to one phone, while Telegram is an
afternoon. That decision should be made before this is written.

Worth deciding alongside it: Q3.5, whether links expire and require auth, or an
unguessable signed URL is enough. A policy-video link is low-stakes, but the
answer changes whether this module needs an auth story at all.
"""

from __future__ import annotations

from owp.models import ScheduledPost
from owp.schedule.base import Notifier


class PushNotifier(Notifier):
    """Sends a push notification with a link to the finished video."""

    def notify(self, post: ScheduledPost) -> None:
        raise NotImplementedError(
            "Notification is not implemented. Blocked on Q3.2 (channel) and Q3.3 (what the "
            "link opens)."
        )
