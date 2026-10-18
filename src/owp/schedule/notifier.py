"""Notification delivery.

STUB. Q3.2 asks for whichever channel is simplest to engineer, and Q3.3/Q3.5
decide most of it: the link opens a small web page carrying the video, caption
and hashtags, and that page requires authentication.

That makes email the simplest channel that still satisfies everything: no
companion app to build and ship to one phone (Firebase push), no bot to
register (Telegram), no per-message cost or carrier rules (SMS). iOS already
pushes mail notifications, which is what Q3.2's 'phone notification' needs.

The authenticated page is the actual work. Simplest on GCP: Cloud Run behind
Identity-Aware Proxy restricted to one Google account, which hands off auth
entirely rather than building sign-in.

Q3.10: pipeline failure and low-inventory alerting is out of scope here -
Cloud Monitoring handles it.
"""

from __future__ import annotations

from owp.models import ScheduledPost


class EmailNotifier:
    """Emails a link to the authenticated review page."""

    def __init__(self, *, to_address: str, review_base_url: str) -> None:
        self.to_address = to_address
        self.review_base_url = review_base_url

    def notify(self, post: ScheduledPost) -> None:
        raise NotImplementedError(
            "Notification is not implemented. Needs the review page to exist first "
            "(Q3.3: video, caption and hashtags on one authenticated page)."
        )
