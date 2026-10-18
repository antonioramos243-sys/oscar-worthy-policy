"""Command-line entry point: `owp <command>`.

Only commands backed by working code are exposed. The stubbed stages are
reachable through `owp.pipeline.Pipeline` once implemented; a CLI full of
commands that only raise would misrepresent what is ready.
"""

from __future__ import annotations

import json
from datetime import datetime

import typer

from owp.acquisition.curated import CuratedTargetSource
from owp.budget import WEEKLY_CAP_USD, estimate_generative_cost
from owp.captions.chunker import cues_from_word_timings
from owp.captions.srt import to_srt
from owp.cast import Cast
from owp.config import Settings
from owp.models import POSTING_TZ, Category, WordTiming
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
    """List the recurring character cast."""
    for character in Cast.load().characters:
        typer.echo(f"{character.id:10} {character.name:16} {character.role}")


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
