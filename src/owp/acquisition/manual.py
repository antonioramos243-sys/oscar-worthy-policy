"""Manual paste-in, the fallback when automated extraction fails (Q1.7).

Some policies are not fetchable: rendered in the browser, behind a consent
wall, or served only to a real browser. Q1.7 settles that as acceptable, and
the only thing the rest of the pipeline needs is that a pasted corpus be
indistinguishable from a fetched one except in its provenance - hence the same
`build_corpus`, and `PolicySource.extracted_manually` to record which it was.

The URL is still required. It is how the policy was found, it is what a
reviewer needs in order to check a claim against the published text (Q2.7),
and a corpus with no source would be unauditable.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from owp.acquisition.http_fetcher import build_corpus
from owp.models import PolicyCorpus, PolicyKind, PolicySource, Target


class MissingPolicyUrl(ValueError):
    """Raised when pasted text has no URL to attribute it to."""


def corpus_from_text(
    target: Target,
    documents: Mapping[PolicyKind, str],
    *,
    urls: Mapping[PolicyKind, str] | None = None,
    fetched_at: datetime | None = None,
) -> PolicyCorpus:
    """Build a corpus from text that was pasted in rather than fetched.

    Args:
        target: The target the text belongs to.
        documents: Policy text per kind. Already text, not HTML - whoever
            pasted it has done the cleaning a browser does.
        urls: Where each document was read, for kinds the target list does not
            carry a URL for.
        fetched_at: When the text was captured. Defaults to now.

    Raises:
        MissingPolicyUrl: when a kind has no URL in `urls` or on the target.
        ValueError: when every document is empty, which is a paste that failed.
    """
    cleaned = {kind: text.strip() for kind, text in documents.items() if text.strip()}
    if not cleaned:
        raise ValueError(f"no policy text pasted for {target.slug}")

    sources = []
    for kind in cleaned:
        url = (urls or {}).get(kind) or target.policy_urls.get(kind)
        if url is None:
            raise MissingPolicyUrl(
                f"no URL for {target.slug} {kind.value}; pass the URL the text was read from"
            )
        # model_validate rather than the constructor so a plain string URL is
        # coerced the same way the target list's URLs are.
        sources.append(
            PolicySource.model_validate(
                {"kind": kind, "url": str(url), "extracted_manually": True}
            )
        )

    return build_corpus(
        target.slug,
        {kind.value: text for kind, text in cleaned.items()},
        sources,
        fetched_at=fetched_at,
    )
