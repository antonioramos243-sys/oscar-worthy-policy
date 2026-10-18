"""Tests for component 1: fetching, cleaning, merging and storing policies.

No test makes a network call. The HTTP path is exercised over an httpx mock
transport serving the HTML fixtures in tests/fixtures/policies, which is also
how a page that 404s, serves a PDF or renders itself in the browser is
reproduced without depending on a site that behaves that way this week.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from owp.acquisition.base import ExtractionFailed
from owp.acquisition.clean import clean_html
from owp.acquisition.http_fetcher import (
    MIN_POLICY_CHARS,
    HttpPolicyFetcher,
    build_corpus,
    content_hash,
    merge_documents,
)
from owp.acquisition.manual import MissingPolicyUrl, corpus_from_text
from owp.acquisition.store import (
    CorpusNotStored,
    corpus_path,
    load_corpus,
    save_corpus,
    stored_slugs,
)
from owp.cli import app
from owp.config import Paths
from owp.models import Category, PolicyKind, PolicySource, Target

FIXTURES = Path(__file__).parent / "fixtures" / "policies"

MAIN_URL = "https://examplegram.example/privacy"
COOKIE_URL = "https://examplegram.example/cookies"

HTML_HEADERS = {"content-type": "text/html; charset=utf-8"}


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text()


def serving(pages: Mapping[str, str]) -> Callable[[httpx.Request], httpx.Response]:
    """A handler answering `pages` with HTML and everything else with 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(str(request.url))
        if body is None:
            return httpx.Response(404, text="Not found", headers=HTML_HEADERS)
        return httpx.Response(200, text=body, headers=HTML_HEADERS)

    return handler


def fetcher(
    handler: Callable[[httpx.Request], httpx.Response], *, respect_robots: bool = False
) -> HttpPolicyFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpPolicyFetcher(client=client, respect_robots=respect_robots)


def target(**policy_urls: str) -> Target:
    return Target.model_validate(
        {
            "slug": "examplegram",
            "company": "Examplegram",
            "category": Category.SOCIAL,
            "rank": 1,
            "policy_urls": policy_urls,
        }
    )


BOTH_POLICIES = target(main_privacy=MAIN_URL, cookie=COOKIE_URL)


# -- merging ----------------------------------------------------------------


def test_every_policy_a_target_publishes_lands_in_one_corpus() -> None:
    # Q1.4: main, cookie and any others merged, so one video can tell a
    # cohesive story rather than one video per document.
    corpus = fetcher(
        serving({MAIN_URL: fixture("main_privacy"), COOKIE_URL: fixture("cookie")})
    ).fetch(BOTH_POLICIES)

    assert corpus.merged_kinds == [PolicyKind.MAIN_PRIVACY, PolicyKind.COOKIE]
    assert "## main_privacy" in corpus.text
    assert "## cookie" in corpus.text
    assert "how long you view them" in corpus.text
    assert "measurement pixel" in corpus.text
    assert corpus.content_hash == content_hash(corpus.text)
    assert corpus.fetched_at.tzinfo is not None
    assert not any(source.extracted_manually for source in corpus.sources)


def test_one_unreachable_policy_does_not_lose_the_others() -> None:
    # A moved cookie policy should not cost us the main one; only a target
    # with nothing usable is worth a human's attention.
    corpus = fetcher(serving({MAIN_URL: fixture("main_privacy")})).fetch(BOTH_POLICIES)

    assert corpus.merged_kinds == [PolicyKind.MAIN_PRIVACY]
    assert "## cookie" not in corpus.text


def test_merge_skips_empty_documents() -> None:
    assert merge_documents({"main_privacy": "Text.", "cookie": "   "}) == "## main_privacy\n\nText."


# -- cleaning ---------------------------------------------------------------


def test_heading_structure_survives_cleaning() -> None:
    # The script writer has to attribute a practice to a section and a reviewer
    # has to find that section again (Q2.7), so nesting is preserved, two
    # levels below the `##` heading `merge_documents` gives each document.
    text = clean_html(fixture("main_privacy"))

    assert "### Privacy Policy" in text
    assert "#### Information we collect" in text
    assert "##### Advertising" in text


def test_paragraph_breaks_survive_cleaning() -> None:
    text = clean_html(fixture("main_privacy"))

    assert "\n\n" in text
    assert "- Precise location, where you have granted permission" in text
    # Wrapped source lines become one paragraph, not one line each.
    assert "collects about you and how we use it." in text


def test_navigation_and_boilerplate_are_dropped() -> None:
    text = clean_html(fixture("main_privacy")) + clean_html(fixture("cookie"))

    for chrome in ("Help Centre", "Download the app", "2026 Examplegram", "Accept all"):
        assert chrome not in text
    assert "window.analytics" not in text
    assert "font-family" not in text


def test_a_container_element_does_not_flatten_the_policy_inside_it() -> None:
    # Regression: real policy pages wrap their content in custom elements
    # (`<c-wiz>` on Google's). Flattening one swallowed every heading and
    # paragraph inside it into a single run of text.
    html = "<main><c-wiz><h2>Retention</h2><p>We keep it.</p><p>For a while.</p></c-wiz></main>"

    assert clean_html(html) == "#### Retention\n\nWe keep it.\n\nFor a while."


def test_an_inline_span_stays_part_of_its_paragraph() -> None:
    html = "<main><p>We <span>collect <b>everything</b></span> about you.</p></main>"

    assert clean_html(html) == "We collect everything about you."


def test_an_inline_tag_used_as_a_container_is_not_flattened() -> None:
    html = "<main><span><h3>Ads</h3><p>We profile you.</p></span></main>"

    assert clean_html(html) == "##### Ads\n\nWe profile you."


def test_cleaning_an_empty_document_yields_nothing() -> None:
    assert clean_html("") == ""


# -- extraction failure -----------------------------------------------------


def test_a_page_that_renders_itself_in_the_browser_raises_extraction_failed() -> None:
    # A JS shell answers 200 with an almost empty body. Treating that as a
    # corpus would produce a video written from nothing, so it fails loudly
    # and the caller pastes the text in instead (Q1.7).
    with pytest.raises(ExtractionFailed, match="paste it in"):
        fetcher(serving({MAIN_URL: fixture("shell")})).fetch(target(main_privacy=MAIN_URL))


def test_extraction_failure_names_every_document_that_failed() -> None:
    with pytest.raises(ExtractionFailed, match="cookie") as caught:
        fetcher(serving({})).fetch(BOTH_POLICIES)

    assert "main_privacy" in str(caught.value)
    assert MAIN_URL in str(caught.value)


def test_a_non_html_response_is_not_treated_as_policy_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"})

    with pytest.raises(ExtractionFailed, match="application/pdf"):
        fetcher(handler).fetch(target(main_privacy=MAIN_URL))


def test_a_target_with_no_policy_urls_raises_rather_than_fetching() -> None:
    with pytest.raises(ExtractionFailed, match="no policy URLs"):
        fetcher(serving({})).fetch(target())


def test_the_minimum_is_a_policy_length_not_a_token() -> None:
    # Guards the constant itself: a threshold low enough to pass a cookie
    # banner would defeat the check.
    assert MIN_POLICY_CHARS >= 200


# -- robots.txt (Q1.10) -----------------------------------------------------


def robots_handler(rules: str) -> Callable[[httpx.Request], httpx.Response]:
    pages = {MAIN_URL: fixture("main_privacy")}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=rules, headers={"content-type": "text/plain"})
        return serving(pages)(request)

    return handler


def test_robots_is_ignored_by_default() -> None:
    # Q1.10: no legal constraints to observe, so the default fetches anyway.
    corpus = fetcher(robots_handler("User-agent: *\nDisallow: /")).fetch(
        target(main_privacy=MAIN_URL)
    )
    assert corpus.text


def test_robots_is_honoured_when_the_flag_is_set() -> None:
    with pytest.raises(ExtractionFailed, match="robots.txt"):
        fetcher(robots_handler("User-agent: *\nDisallow: /"), respect_robots=True).fetch(
            target(main_privacy=MAIN_URL)
        )


def test_robots_allowing_the_path_still_fetches() -> None:
    corpus = fetcher(
        robots_handler("User-agent: *\nDisallow: /admin"), respect_robots=True
    ).fetch(target(main_privacy=MAIN_URL))
    assert corpus.text


# -- manual upload (Q1.7) ---------------------------------------------------


def test_pasted_text_becomes_a_corpus_marked_as_manual() -> None:
    corpus = corpus_from_text(
        BOTH_POLICIES,
        {PolicyKind.MAIN_PRIVACY: "  We collect everything.  "},
        fetched_at=datetime(2026, 10, 17, tzinfo=UTC),
    )

    assert corpus.text == "## main_privacy\n\nWe collect everything."
    assert corpus.content_hash == content_hash(corpus.text)
    assert [source.extracted_manually for source in corpus.sources] == [True]
    assert str(corpus.sources[0].url) == MAIN_URL


def test_pasted_text_can_supply_its_own_url() -> None:
    corpus = corpus_from_text(
        target(),
        {PolicyKind.COOKIE: "We use cookies."},
        urls={PolicyKind.COOKIE: "https://elsewhere.example/cookies"},
    )
    assert str(corpus.sources[0].url) == "https://elsewhere.example/cookies"


def test_pasted_text_with_no_url_anywhere_is_refused() -> None:
    # A corpus with no source is unauditable: a reviewer could not check a
    # claim against the published policy (Q2.7).
    with pytest.raises(MissingPolicyUrl, match="main_privacy"):
        corpus_from_text(target(), {PolicyKind.MAIN_PRIVACY: "Text."})


def test_an_empty_paste_is_refused() -> None:
    with pytest.raises(ValueError, match="no policy text"):
        corpus_from_text(BOTH_POLICIES, {PolicyKind.MAIN_PRIVACY: "\n  \n"})


# -- content hash -----------------------------------------------------------


def reflowed(html: str) -> str:
    """The same page, differently marked up: wrappers, nbsp and odd spacing."""
    return (
        html.replace("<p>", '<div class="rail"><span><p style="margin:0">')
        .replace("</p>", "</p></span></div>")
        .replace(" ", "  ")
        .replace("\n", "\n\t")
        .replace("Effective", "Effective​")
    )


def test_content_hash_survives_whitespace_and_markup_churn() -> None:
    # Q1.6 takes one snapshot, so there is no history to diff a spurious
    # change against: the hash has to mean "the wording changed".
    pages = {MAIN_URL: fixture("main_privacy")}
    churned = {MAIN_URL: reflowed(fixture("main_privacy"))}

    first = fetcher(serving(pages)).fetch(target(main_privacy=MAIN_URL))
    second = fetcher(serving(churned)).fetch(target(main_privacy=MAIN_URL))

    assert first.text == second.text
    assert first.content_hash == second.content_hash


def test_content_hash_changes_when_the_wording_changes() -> None:
    pages = {MAIN_URL: fixture("main_privacy")}
    reworded = {MAIN_URL: fixture("main_privacy").replace("how long you view them", "nothing")}

    first = fetcher(serving(pages)).fetch(target(main_privacy=MAIN_URL))
    second = fetcher(serving(reworded)).fetch(target(main_privacy=MAIN_URL))

    assert first.content_hash != second.content_hash


def test_hash_is_over_the_merged_text_not_the_documents() -> None:
    corpus = build_corpus(
        "examplegram",
        {"main_privacy": "A." * 10},
        [PolicySource.model_validate({"kind": PolicyKind.MAIN_PRIVACY, "url": MAIN_URL})],
    )
    assert corpus.content_hash == content_hash(corpus.text)


# -- storage ----------------------------------------------------------------


def paths_in(tmp_path: Path) -> Paths:
    return Paths(policies=tmp_path / "policies", renders=tmp_path / "renders")


def test_a_corpus_round_trips_through_disk(tmp_path: Path) -> None:
    paths = paths_in(tmp_path)
    original = fetcher(
        serving({MAIN_URL: fixture("main_privacy"), COOKIE_URL: fixture("cookie")})
    ).fetch(BOTH_POLICIES)

    path = save_corpus(original, paths=paths)
    loaded = load_corpus("examplegram", paths=paths)

    assert path == corpus_path("examplegram", paths=paths)
    assert loaded == original
    assert loaded.content_hash == content_hash(loaded.text)
    assert loaded.merged_kinds == original.merged_kinds


def test_refetching_overwrites_the_one_snapshot(tmp_path: Path) -> None:
    # Q1.6: one snapshot per target, no version history.
    paths = paths_in(tmp_path)
    first = build_corpus("examplegram", {"main_privacy": "Old wording."}, [])
    second = build_corpus("examplegram", {"main_privacy": "New wording."}, [])

    save_corpus(first, paths=paths)
    save_corpus(second, paths=paths)

    assert stored_slugs(paths=paths) == ["examplegram"]
    assert load_corpus("examplegram", paths=paths).text == second.text


def test_loading_a_target_that_was_never_fetched_says_so(tmp_path: Path) -> None:
    with pytest.raises(CorpusNotStored, match="owp fetch tinder"):
        load_corpus("tinder", paths=paths_in(tmp_path))


def test_no_stored_slugs_before_anything_is_fetched(tmp_path: Path) -> None:
    assert stored_slugs(paths=paths_in(tmp_path)) == []


# -- CLI --------------------------------------------------------------------


def test_fetch_command_stores_a_pasted_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = paths_in(tmp_path)
    monkeypatch.setattr("owp.cli.save_corpus", lambda corpus: save_corpus(corpus, paths=paths))

    pasted = tmp_path / "policy.txt"
    pasted.write_text("We collect everything you do.")

    result = CliRunner().invoke(
        app,
        [
            "fetch",
            "instagram",
            "--paste",
            str(pasted),
            "--url",
            f"main_privacy={MAIN_URL}",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "1 pasted in" in result.output
    stored = load_corpus("instagram", paths=paths)
    assert stored.text.endswith("We collect everything you do.")
    assert str(stored.sources[0].url) == MAIN_URL


def test_fetch_command_refuses_a_paste_with_nowhere_to_attribute_it(tmp_path: Path) -> None:
    # The curated list ships without URLs, so a bare --paste has no source.
    pasted = tmp_path / "policy.txt"
    pasted.write_text("We collect everything you do.")

    result = CliRunner().invoke(app, ["fetch", "instagram", "--paste", str(pasted)])

    assert result.exit_code == 1
    assert "--url main_privacy=" in result.output


def test_fetch_command_rejects_an_unknown_target() -> None:
    result = CliRunner().invoke(app, ["fetch", "not-a-target"])
    assert result.exit_code == 1
    assert "Unknown target" in result.output


def test_fetch_command_rejects_a_malformed_url_override() -> None:
    result = CliRunner().invoke(app, ["fetch", "instagram", "--url", "main_privacy"])
    assert result.exit_code == 1
    assert "KIND=URL" in result.output


def test_policy_command_reports_a_target_that_was_never_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = paths_in(tmp_path)
    monkeypatch.setattr("owp.cli.load_corpus", lambda slug: load_corpus(slug, paths=paths))

    result = CliRunner().invoke(app, ["policy", "tinder"])

    assert result.exit_code == 1
    assert "no stored policy corpus" in result.output
