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
| 1. Policy acquisition | `owp.acquisition` | **Works**: target list, fetch, clean, merge, store, manual paste-in |
| 2a. Script writer | `owp.script` | Stubbed; quote + cast verification **work** |
| 2b. Voiceover | `owp.voice` | Stubbed (Cloud TTS) |
| 2c. Captions | `owp.captions` | **Works** — cue chunking and SRT |
| 2d. Render | `owp.render` | **Hybrid chosen**; plan resolution works, ffmpeg stubbed |
| — Plate library | `owp.render.plates` | **Works** — reusable backgrounds, budget-aware batching |
| — Character cast | `owp.cast` | **Works** — cast registry; artwork not drawn |
| — Budget cap | `owp.budget` | **Works** — $25/week enforced before spending |
| 3. Schedule | `owp.schedule.slots` | **Works** — 4/week, Eastern, 09:00–22:00 |
| 3. Notify | `owp.schedule.notifier` | Stubbed (email; needs the review page) |
| 4. Metrics | `owp.metrics` | Stubbed (Creator account confirmed) |
| 4. Optimizer | `owp.optimize` | **Works** — factored bandit, objective, 5 variables |

**Before anything renders:** the cast has to be drawn. `cast.json` holds
placeholder appearances with no `asset_dir`, and `plates.json` holds four
placeholder prompts. That is the gating dependency now — not a decision.

## Setup

Requires [uv](https://docs.astral.sh/uv/). System Python here is 3.9; the
project needs 3.12, which uv will fetch.

```bash
uv venv --python 3.12
uv pip install -e ".[acquisition,dev]"
cp .env.example .env
```

Needed when the matching stage is built, not installed yet: `ffmpeg`
(rendering), `gcloud` (deploys).

## Try the parts that work

```bash
.venv/bin/owp targets    # the 40-target set and what it is missing
.venv/bin/owp fetch google-search \
  --url "main_privacy=https://policies.google.com/privacy?hl=en-US" \
  --url "cookie=https://policies.google.com/technologies/cookies?hl=en-US"
.venv/bin/owp policy google-search   # read the stored corpus back

.venv/bin/owp plates     # background plate library and what fits this week
.venv/bin/owp slots      # next posting slots, Eastern, inside quiet hours
.venv/bin/owp budget     # which generation tiers fit $25/week
.venv/bin/owp cast       # the recurring characters
.venv/bin/owp arms       # size of the optimizer's variant space
```

`fetch` takes `--url` because the curated list is still a placeholder and
carries no policy URLs; filling those in belongs with the popularity ranking.
When a page cannot be extracted, paste the text instead (Q1.7):
`owp fetch <slug> --paste policy.txt --url main_privacy=<url>`.

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

**Rendering is hybrid: drawn characters over generated backgrounds.** Each
technique is used where it is strong. Backgrounds come from a generated plate
library built once and reused, so visual variety is cheap; characters are drawn
assets composited on top, so consistency across videos is structural rather
than something a model has to hold. See
[docs/requirements-decisions.md](docs/requirements-decisions.md).

**The plate library is reusable by design, and that is what makes the budget
work.** Generating backgrounds per video costs ~$12/week forever, half the cap.
Generating them once costs ~$24 one-off for 60 plates, after which a video
costs about $0.16 — $0.64/week at four a week. `PlateLibrary.affordable_batch`
truncates a batch to what the week affords instead of rejecting it, so the
library grows weekly.

**Character consistency is a state problem, not a rendering problem.** The cast
lives in `cast.json` with a stable id per character, and `verify_cast` fails a
script that names an unknown one before anything renders.

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
