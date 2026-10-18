"""Turning engagement into a single number the optimizer can maximize.

Q4.2 names the objective as informing people about the poor privacy practices
of large companies. That is a mission, not a metric, so it needs a measurable
proxy - and the choice of proxy is a real decision, not a formality, because
the bandit will optimize whatever this function returns.

`reach` is the proxy: the number of distinct accounts that saw the video, which
is as close as the Graph API gets to 'people informed'. Shares are added with a
weight because a share is not just engagement, it is distribution - it produces
future reach, which is the objective itself.

Views are deliberately not the objective: a view is counted at a fraction of a
second and a single viewer can produce several, so maximizing views rewards
thumb-stopping that informs nobody. Follows and saves are reported but not
scored; they measure audience building, which Q4.2 does not ask for.

SHARE_WEIGHT is a starting point, not a finding. Revisit it once there is
enough data to regress reach on prior-post shares.
"""

from __future__ import annotations

from owp.models import PostMetrics

SHARE_WEIGHT = 10.0


class MetricsUnavailable(ValueError):
    """Raised when a metrics record has no reach, so it cannot be scored."""


def informed_score(metrics: PostMetrics) -> float:
    """The optimizer's objective: reach, plus weighted shares.

    Raises:
        MetricsUnavailable: if `reach` is missing. Scoring a partial record as
            zero would teach the bandit that the variant failed, which is worse
            than having no observation at all.
    """
    if metrics.reach is None:
        raise MetricsUnavailable(
            f"{metrics.instagram_url} at {metrics.window.value} has no reach; cannot score"
        )
    return float(metrics.reach) + SHARE_WEIGHT * float(metrics.shares or 0)
