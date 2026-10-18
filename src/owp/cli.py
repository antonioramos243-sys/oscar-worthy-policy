"""Command-line entry point: `owp <command>`.

Only the commands that work today are wired up. The rest of the pipeline is
reachable through `owp.pipeline.Pipeline` once its stages are implemented;
exposing stub commands that only raise would make the CLI lie about what is
ready.
"""

from __future__ import annotations

import json

import typer

from owp.acquisition.curated import CuratedTargetSource
from owp.captions.chunker import cues_from_word_timings
from owp.captions.srt import to_srt
from owp.config import Settings
from owp.models import Category, WordTiming

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
        typer.echo("Curated list is a placeholder pending the popularity measure (Q1.2).")


@app.command()
def captions(timings_json: typer.FileText) -> None:
    """Convert a word-timings JSON file into SRT on stdout.

    Expects a list of {"word", "start_s", "end_s"} objects, which is what the
    TTS stage will emit. Lets the captions stage be exercised before TTS exists.
    """
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
