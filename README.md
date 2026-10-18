# oscar-worthy-policy

Turns the privacy policies of popular apps into short narrative videos for Instagram.

Pipeline:

```
target -> policy snapshot -> script (cited) -> verify -> voiceover -> captions
       -> render -> schedule -> phone notification -> [manual post] -> metrics
```

The system never posts. It produces a finished video and notifies a phone at the
scheduled time; posting is manual.

## Status

Scaffold. The stage boundaries, domain model, and accuracy gates are in place;
most stages raise `NotImplementedError` with the decision that blocks them. See
[docs/requirements-open-questions.md](docs/requirements-open-questions.md).

| Component | Module | State |
|---|---|---|
| 1. Policy acquisition | `owp.acquisition` | Target list works; fetching stubbed (Q1.10, Q1.4) |
| 2a. Script writer | `owp.script` | Stubbed (Q2.1, Q2.6, Q2.8, Q2.9); citation check **works** |
| 2b. Voiceover | `owp.voice` | Stubbed (Q2.5) |
| 2c. Captions | `owp.captions` | **Works** — cue chunking and SRT |
| 2d. Render | `owp.render` | Stubbed (Q2.4 — style choice changes the implementation) |
| 3. Schedule + notify | `owp.schedule` | Stubbed (Q3.2, Q3.3) |
| 4. Metrics | `owp.metrics` | Stubbed (Q4.1 — needs a Business/Creator account) |
| 4. Optimizer | — | Not scaffolded; no primary objective chosen yet (Q4.2) |

## Setup

Requires [uv](https://docs.astral.sh/uv/). The system Python here is 3.9; the
project needs 3.12, which uv will fetch.

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Then:

```bash
cp .env.example .env   # fill in as credentials become available
.venv/bin/owp config   # show resolved settings
.venv/bin/owp targets  # list targets and what the set is missing
```

Not yet installed on this machine, needed when the matching stage is built:

- `ffmpeg` — rendering (`brew install ffmpeg`)
- `gcloud` — GCP deploys (`brew install --cask google-cloud-sdk`)
- `terraform` — infrastructure, if used

## Try the part that works

Captions are derived from the TTS stage's word timings, so they can be
exercised before TTS exists:

```bash
echo '[{"word":"They","start_s":0.0,"end_s":0.3},{"word":"know","start_s":0.3,"end_s":0.6}]' \
  | .venv/bin/owp captions /dev/stdin
```

## Checks

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

## Design notes

**Accuracy is a gate, not a score.** `owp.script.verify.verify_citations`
requires every cited quote to appear verbatim in the policy snapshot, and
`Pipeline.draft` runs it outside the writer so no writer can skip it.
`Pipeline.produce` additionally refuses to render a script that is not marked
reviewed.

**Captions come from TTS timepoints, not forced alignment.** Google Cloud TTS
reports timepoints for SSML `<mark>` elements; feeding those into
`cues_from_word_timings` avoids a whole alignment dependency. Alignment is the
fallback if the voice stage changes.

**Snapshots are immutable.** `PolicySnapshot.content_hash` is over cleaned text
rather than raw HTML, so markup churn doesn't register as a policy change.
`Script.content_hash` records which snapshot it was written from, so a script
can be invalidated when its policy changes.

**Stages are Protocols.** The undecided stages have more than one plausible
implementation (five visual styles, six notification channels, two voice
approaches), so each is an interface with a stub behind it.

> **This repository is public.** Never commit service-account JSON, API keys, or
> Instagram tokens. `.gitignore` covers the usual names, but it is not a
> substitute for checking `git diff --staged`.
