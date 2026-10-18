"""Command-line entry point: `owp <command>`.

Only commands backed by working code are exposed. The stubbed stages are
reachable through `owp.pipeline.Pipeline` once implemented; a CLI full of
commands that only raise would misrepresent what is ready.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from owp.acquisition.base import ExtractionFailed
from owp.acquisition.curated import CuratedTargetSource
from owp.acquisition.http_fetcher import HttpPolicyFetcher
from owp.acquisition.manual import MissingPolicyUrl, corpus_from_text
from owp.acquisition.store import CorpusNotStored, load_corpus, save_corpus
from owp.budget import WEEKLY_CAP_USD, estimate_generative_cost
from owp.captions.chunker import cues_from_word_timings
from owp.captions.srt import to_srt
from owp.cast import Cast
from owp.config import Settings
from owp.models import POSTING_TZ, Category, PolicyCorpus, PolicyKind, Target, WordTiming
from owp.optimize.arms import all_arms
from owp.render.plates import DEFAULT_USD_PER_SECOND, PlateLibrary
from owp.schedule.slots import DEFAULT_PER_WEEK, slots

app = typer.Typer(help="Oscar Worthy Policy - privacy policies as short narrative videos.")


@app.command()
def targets(category: Category | None = None) -> None:
    """List the curated target companies and what the set is still missing."""
    source = CuratedTargetSource()
    for target in source.targets(category):
        typer.echo(f"{target.category.value:8} {target.rank or '-':>3}  {target.company}")

    shortfall = source.shortfall()
    if shortfall:
        typer.echo("")
        missing = ", ".join(f"{cat.value} +{n}" for cat, n in shortfall.items())
        typer.echo(f"Incomplete target set: {missing}")


@app.command()
def fetch(
    slug: str,
    url: Annotated[
        list[str] | None,
        typer.Option(
            "--url",
            help="KIND=URL, repeatable. Overrides the target list, which ships without URLs.",
        ),
    ] = None,
    paste: Annotated[
        Path | None,
        typer.Option(help="A file of already-extracted policy text, instead of fetching (Q1.7)."),
    ] = None,
    paste_kind: Annotated[
        PolicyKind, typer.Option(help="Which policy the --paste file is.")
    ] = PolicyKind.MAIN_PRIVACY,
    robots: Annotated[bool, typer.Option(help="Honour robots.txt (Q1.10: off).")] = False,
) -> None:
    """Fetch, merge and store one target's policies (Q1.4).

    Every policy the target publishes is merged into one corpus. When a page
    cannot be extracted, re-run with --paste pointing at the text (Q1.7).
    """
    target = _target(slug, url or [])

    if paste is not None:
        try:
            corpus = corpus_from_text(target, {paste_kind: paste.read_text()})
        except MissingPolicyUrl as exc:
            # The URL is what a reviewer checks a claim against (Q2.7), so
            # pasted text still has to say where it was read.
            typer.echo(f"{exc}: --url {paste_kind.value}=https://...", err=True)
            raise typer.Exit(1) from exc
    else:
        try:
            corpus = HttpPolicyFetcher(respect_robots=robots).fetch(target)
        except ExtractionFailed as exc:
            typer.echo(f"Extraction failed: {exc}", err=True)
            typer.echo(f"Fallback: owp fetch {slug} --paste policy.txt", err=True)
            raise typer.Exit(1) from exc

    path = save_corpus(corpus)
    _describe(corpus)
    typer.echo(f"stored:  {path}")


@app.command()
def policy(
    slug: str,
    chars: Annotated[
        int, typer.Option(help="Characters of text to print; 0 for the whole corpus.")
    ] = 600,
) -> None:
    """Show a stored policy corpus."""
    try:
        corpus = load_corpus(slug)
    except CorpusNotStored as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    _describe(corpus)
    typer.echo("")
    typer.echo(corpus.text if chars <= 0 else corpus.text[:chars])


def _target(slug: str, url_overrides: list[str]) -> Target:
    """Look a target up in the curated list and apply any --url overrides."""
    matches = [t for t in CuratedTargetSource().targets() if t.slug == slug]
    if not matches:
        typer.echo(f"Unknown target {slug!r}; see `owp targets`.", err=True)
        raise typer.Exit(1)

    policy_urls = {kind.value: str(url) for kind, url in matches[0].policy_urls.items()}
    for override in url_overrides:
        kind, _, value = override.partition("=")
        if not value:
            typer.echo(f"--url wants KIND=URL, got {override!r}", err=True)
            raise typer.Exit(1)
        if kind not in {k.value for k in PolicyKind}:
            kinds = ", ".join(k.value for k in PolicyKind)
            typer.echo(f"Unknown policy kind {kind!r}; one of: {kinds}", err=True)
            raise typer.Exit(1)
        policy_urls[kind] = value

    # Revalidated so an overridden URL is checked like one from the target list.
    return Target.model_validate({**matches[0].model_dump(), "policy_urls": policy_urls})


def _describe(corpus: PolicyCorpus) -> None:
    merged = ", ".join(kind.value for kind in corpus.merged_kinds)
    manual = sum(1 for source in corpus.sources if source.extracted_manually)
    typer.echo(f"{corpus.target_slug}: {len(corpus.text):,} characters")
    typer.echo(f"merged:  {merged}" + (f" ({manual} pasted in)" if manual else ""))
    typer.echo(f"hash:    {corpus.content_hash[:16]}")
    typer.echo(f"fetched: {corpus.fetched_at.isoformat(timespec='seconds')}")


@app.command(name="slots")
def show_slots(count: int = 8, per_week: int = DEFAULT_PER_WEEK) -> None:
    """Show the next posting slots (Eastern, 09:00-22:00)."""
    now = datetime.now(POSTING_TZ)
    for slot in slots(now, count, per_week=per_week):
        typer.echo(slot.strftime("%a %Y-%m-%d %H:%M %Z"))


@app.command()
def budget(per_week: int = DEFAULT_PER_WEEK, seconds: float = 60.0) -> None:
    """Show which generation tiers fit the weekly cap at a given cadence."""
    tiers = {
        "Veo 3.1 Lite 720p": 0.05,
        "Veo 3.1 Lite 1080p": 0.08,
        "Veo 3.1 Fast": 0.20,
        "Veo 3.1 Standard": 0.50,
        "Asset-based (local)": 0.0,
    }
    typer.echo(f"Cap ${WEEKLY_CAP_USD:.2f}/week at {per_week}x {seconds:.0f}s videos:")
    for name, rate in tiers.items():
        weekly = per_week * estimate_generative_cost(seconds, rate)
        verdict = "fits" if weekly <= WEEKLY_CAP_USD else "OVER"
        typer.echo(f"  {name:22} ${weekly:7.2f}/wk  {verdict}")


@app.command()
def cast() -> None:
    """List the cast - the CEOs of the covered companies - and what is missing."""
    loaded = Cast.load()
    for character in loaded.characters:
        verified = character.verified_on.isoformat() if character.verified_on else "UNVERIFIED"
        company = character.company or "-"
        typer.echo(f"{character.id:12} {character.name:18} {company:18} {verified}")
        covers = ", ".join(character.target_slugs) or "(no targets yet)"
        typer.echo(f"{'':12} covers {covers}")

    missing = loaded.missing_for(t.slug for t in CuratedTargetSource().targets())
    if missing:
        typer.echo("")
        typer.echo(f"No cast member yet for: {', '.join(missing)}")


@app.command()
def arms() -> None:
    """Report the size of the optimizer's variant space."""
    typer.echo(f"{len(all_arms())} arms across 5 variables")


@app.command()
def plates(reserve: float = 0.64) -> None:
    """Show the background plate library and what fits this week's budget.

    `reserve` holds back budget for the week's videos (4 x $0.16 by default).
    """
    from datetime import datetime as _dt

    library = PlateLibrary.load()
    ready, pending = library.generated(), library.pending()
    typer.echo(f"{len(ready)} generated, {len(pending)} pending")

    if pending:
        full = library.generation_cost(pending, usd_per_second=DEFAULT_USD_PER_SECOND)
        batch = library.affordable_batch(
            [], _dt.now(POSTING_TZ), usd_per_second=DEFAULT_USD_PER_SECOND, reserve_usd=reserve
        )
        batch_cost = library.generation_cost(batch, usd_per_second=DEFAULT_USD_PER_SECOND)
        typer.echo(f"all pending would cost ${full:.2f}")
        typer.echo(
            f"affordable now:  {len(batch)} plates, ${batch_cost:.2f} "
            f"(reserve ${reserve:.2f})"
        )

    for plate in library.plates:
        mark = "ready  " if plate.generated else "pending"
        typer.echo(f"  {mark} {plate.style.value:10} {plate.id}")


@app.command()
def captions(timings_json: typer.FileText) -> None:
    """Convert a word-timings JSON file into SRT on stdout."""
    words = [WordTiming.model_validate(entry) for entry in json.load(timings_json)]
    typer.echo(to_srt(cues_from_word_timings(words)), nl=False)


@app.command()
def config() -> None:
    """Show resolved settings and which credentials are missing."""
    settings = Settings.from_env()
    typer.echo(f"gcp_project:  {settings.gcp_project or '(unset)'}")
    typer.echo(f"gcs_bucket:   {settings.gcs_bucket or '(unset)'}")
    typer.echo(f"region:       {settings.region}")
    typer.echo(f"llm_provider: {settings.llm_provider}")
    typer.echo(f"ig_user_id:   {settings.ig_user_id or '(unset)'}")


if __name__ == "__main__":
    app()
