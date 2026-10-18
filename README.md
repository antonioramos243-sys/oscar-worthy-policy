# oscar-worthy-policy

Turns the privacy policies of popular apps into short narrative videos for Instagram.

```
target -> merged policy corpus -> script (per practice) -> verify -> voiceover
       -> captions -> animate -> schedule -> email notification
       -> [manual post] -> metrics -> bandit
```

The system never posts. It produces a finished video and emails a link to an
authenticated review page at the scheduled time; posting is manual, and the
Instagram URL is pasted back afterwards.

Requirements are settled: see [docs/requirements-decisions.md](docs/requirements-decisions.md).
39 of 40 questions are answered, and that file lists the four gaps that remain.

## Status

| Component | Module | State |
|---|---|---|
| 1. Policy acquisition | `owp.acquisition` | Target list + duplicate check **work**; fetch/merge stubbed |
| 2a. Script writer | `owp.script` | Stubbed; quote + cast verification **work** |
| 2b. Voiceover | `owp.voice` | Stubbed (Cloud TTS) |
| 2c. Captions | `owp.captions` | **Works** — cue chunking and SRT |
| 2d. Render | `owp.render` | Two paths scaffolded; **animation approach not decided** |
| — Character cast | `owp.cast` | **Works** — cast registry; artwork not drawn |
| — Budget cap | `owp.budget` | **Works** — $25/week enforced before spending |
| 3. Schedule | `owp.schedule.slots` | **Works** — 4/week, Eastern, 09:00–22:00 |
| 3. Notify | `owp.schedule.notifier` | Stubbed (email; needs the review page) |
| 4. Metrics | `owp.metrics` | Stubbed (Creator account confirmed) |
| 4. Optimizer | `owp.optimize` | **Works** — factored bandit, objective, 5 variables |

## Setup

Requires [uv](https://docs.astral.sh/uv/). System Python here is 3.9; the
project needs 3.12, which uv will fetch.

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env
```

Needed when the matching stage is built, not installed yet: `ffmpeg`
(rendering), `gcloud` (deploys).

## Try the parts that work

```bash
.venv/bin/owp targets    # the 40-target set and what it is missing
.venv/bin/owp slots      # next posting slots, Eastern, inside quiet hours
.venv/bin/owp budget     # which generation tiers fit $25/week
.venv/bin/owp cast       # the recurring characters
.venv/bin/owp arms       # size of the optimizer's variant space
```

## Checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

## Design notes

**The $25/week cap is enforced in code, not by a billing alert.** The dominant
cost is billed per second of generated video, so `Pipeline.produce` checks
`owp.budget.check_affordable` *before* rendering. A billing alert tells you
after the money is gone.

**Character consistency is a state problem, not a rendering problem.** Q2.4
wants the same characters across every video, so the cast lives in `cast.json`
with a stable id per character, and `verify_cast` fails a script that names an
unknown one. Both renderers read the same cast.

**Captions come from TTS timepoints, not forced alignment.** Cloud TTS reports
timepoints for SSML `<mark>` elements; feeding those to
`cues_from_word_timings` avoids an alignment dependency.

**The bandit learns per variable, not per arm.** The space is 675 arms and the
cadence is four posts a week, so a per-arm bandit would never leave its first
pull. Each observation updates all five dimensions instead. That gives up
interaction effects to learn anything at all at this volume.

**Accuracy and tone are not optimizer variables.** Q4.6 makes them hard
constraints, enforced by absence from the arm space — a constraint that is
merely weighted is one that eventually gets traded away.

**Quote verification is not an accuracy gate.** Q2.7 puts accuracy on personal
review. `verify_quotes` catches one thing review is bad at: a fluent quote the
policy never contained.

> **This repository is public.** Never commit service-account JSON, API keys, or
> Instagram tokens. `.gitignore` covers the usual names; it is not a substitute
> for checking `git diff --staged`.
