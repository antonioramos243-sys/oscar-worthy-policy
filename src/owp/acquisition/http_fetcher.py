"""Fetches policy pages over HTTP, cleans them, and merges them per target.

Fetch the US version (Q1.5) of each policy a target publishes, clean it to text
(Q1.8), concatenate the documents under per-document headings (Q1.4), and store
the result once with no version history (Q1.6).

One document failing does not fail the target: a company that has moved its
cookie policy should still yield a corpus from its main policy. `fetch` only
raises when nothing usable came back at all, because that is the case the
caller can act on - paste the text in by hand (Q1.7).

On robots.txt: Q1.10 says there are no legal constraints to observe, so
`respect_robots` defaults to False. The flag is honoured when set rather than
merely accepted, because privacy-policy pages are almost always crawl-allowed
and turning it on is therefore unlikely to cost coverage if that is revisited.

httpx and selectolax are the `acquisition` extra, imported inside the methods
that need them so the rest of the CLI works without them installed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from owp.acquisition.base import ExtractionFailed, PolicyFetcher
from owp.acquisition.clean import clean_html
from owp.models import PolicyCorpus, PolicySource, Target

if TYPE_CHECKING:
    import httpx

#: Identifies the crawler to a site and to its robots.txt.
USER_AGENT = "owp-policy-fetcher/0.1 (+https://github.com/antonioramos243-sys/oscar-worthy-policy)"

#: Q1.5 wants the US edition and Q1.9 English, and content negotiation is the
#: cheapest lever for both: most policy sites redirect or localize on this.
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

#: Below this many characters a page is chrome, not a policy. Consent walls and
#: pages that render their text in the browser both answer 200 with an almost
#: empty body, and treating that as a corpus would quietly produce a video
#: written from nothing. Manual paste-in is the fallback (Q1.7), so failing
#: loudly here is cheap and silence is not.
MIN_POLICY_CHARS = 500


def content_hash(text: str) -> str:
    """sha256 over cleaned text, so a script can be tied to the corpus it used."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_documents(parts: dict[str, str]) -> str:
    """Join cleaned documents into one corpus under stable headings.

    Headings are kept so the script writer can attribute a practice to the
    cookie policy rather than the main one, and so a reviewer can find it.
    """
    return "\n\n".join(
        f"## {name}\n\n{text.strip()}" for name, text in parts.items() if text.strip()
    )


def build_corpus(
    target_slug: str,
    documents: dict[str, str],
    sources: list[PolicySource],
    *,
    fetched_at: datetime | None = None,
) -> PolicyCorpus:
    """Merge cleaned documents into the corpus for one target.

    Shared by the HTTP path and the manual paste-in path (Q1.7) so both produce
    a corpus whose `content_hash` is computed the same way, and a corpus that
    was pasted in is comparable with one that was fetched.
    """
    merged = merge_documents(documents)
    return PolicyCorpus(
        target_slug=target_slug,
        fetched_at=fetched_at or datetime.now(UTC),
        text=merged,
        sources=sources,
        content_hash=content_hash(merged),
    )


class HttpPolicyFetcher(PolicyFetcher):
    """Retrieves, cleans and merges policy documents."""

    def __init__(
        self,
        *,
        respect_robots: bool = False,
        timeout_s: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        """
        Args:
            respect_robots: Check robots.txt before each URL (Q1.10: off).
            timeout_s: Per-request timeout.
            client: An httpx client to use instead of opening one. Tests pass a
                client over a mock transport; callers fetching many targets can
                pass one to reuse connections.
        """
        self.respect_robots = respect_robots
        self.timeout_s = timeout_s
        self._client = client
        self._robots: dict[str, RobotFileParser] = {}

    def fetch(self, target: Target) -> PolicyCorpus:
        """Fetch and merge every in-scope policy for one target (Q1.4)."""
        if not target.policy_urls:
            raise ExtractionFailed(
                f"{target.slug} has no policy URLs in the target list; "
                "paste the text in instead (Q1.7)."
            )

        documents: dict[str, str] = {}
        sources: list[PolicySource] = []
        failures: list[str] = []

        with self._open() as client:
            for kind, url in target.policy_urls.items():
                try:
                    documents[kind.value] = self._fetch_one(client, str(url))
                except ExtractionFailed as exc:
                    failures.append(f"{kind.value} <{url}>: {exc}")
                    continue
                sources.append(PolicySource(kind=kind, url=url))

        if not documents:
            raise ExtractionFailed(
                f"no usable policy text for {target.slug}; paste it in instead (Q1.7). "
                + "; ".join(failures)
            )
        return build_corpus(target.slug, documents, sources)

    def _fetch_one(self, client: httpx.Client, url: str) -> str:
        """Fetch one URL and return its cleaned text.

        Raises:
            ExtractionFailed: on a transport error, a non-2xx response, a
                non-HTML body, or too little text to be a policy.
        """
        import httpx

        if self.respect_robots and not self._robots_allows(client, url):
            raise ExtractionFailed("disallowed by robots.txt")

        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExtractionFailed(str(exc)) from exc

        content_type = response.headers.get("content-type", "")
        if content_type and "html" not in content_type and "text/plain" not in content_type:
            raise ExtractionFailed(f"not an HTML document (content-type {content_type!r})")

        text = clean_html(response.text)
        if len(text) < MIN_POLICY_CHARS:
            raise ExtractionFailed(
                f"{len(text)} characters of text, below the {MIN_POLICY_CHARS} "
                "needed to be a policy"
            )
        return text

    def _robots_allows(self, client: httpx.Client, url: str) -> bool:
        """Whether robots.txt permits `url`, caching one parse per host.

        An unreachable or non-2xx robots.txt is read as allow-all, which is how
        the usual crawlers read it.
        """
        import httpx

        split = urlsplit(url)
        robots_url = urlunsplit((split.scheme, split.netloc, "/robots.txt", "", ""))

        parser = self._robots.get(robots_url)
        if parser is None:
            parser = RobotFileParser()
            try:
                response = client.get(robots_url)
            except httpx.HTTPError:
                parser.parse([])
            else:
                parser.parse(response.text.splitlines() if response.is_success else [])
            self._robots[robots_url] = parser

        return parser.can_fetch(USER_AGENT, url)

    @contextmanager
    def _open(self) -> Iterator[httpx.Client]:
        """Yield the injected client, or one opened and closed for this fetch."""
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - depends on the install
            raise ImportError(
                "Policy fetching needs the acquisition extra: pip install 'owp[acquisition]'"
            ) from exc

        if self._client is not None:
            yield self._client
            return
        with httpx.Client(
            timeout=self.timeout_s, follow_redirects=True, headers=DEFAULT_HEADERS
        ) as client:
            yield client
