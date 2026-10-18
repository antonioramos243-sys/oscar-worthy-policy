# Open requirements questions

Source of record: the "Privacy Policy Videos MVP: Requirements Questions"
Google Doc. Answers belong there, as comments on the questions; this file only
maps questions onto the code they block, so the scaffold says why each stub is
a stub.

Question numbers below match the doc: `Q<component>.<number>`.

## Already decided

- **Policy set:** 40 policies — 10 social platforms, 10 dating apps, 5 AI apps,
  15 top websites/apps. Encoded in `owp.acquisition.curated.EXPECTED_COUNTS`.
- **Popularity data:** third party, e.g. Sensor Tower.
- **Platform:** Google Cloud Platform.
- **Distribution:** Instagram only, posted manually from Antonio's phone.
- **Notification:** phone notification at the scheduled posting time, carrying
  a link to the video.

## Blocking — a module cannot be written until these are answered

| Q | Question | Blocks | Note |
|---|---|---|---|
| Q2.4 | Visual style: AI footage, animation, stock montage, avatar, or text over b-roll | `owp.render.ffmpeg_renderer` | The five options are different pipelines, not config. Only text-over-b-roll is a pure ffmpeg job; Veo-generated footage barely shares code with it. **Highest-leverage question in the set.** |
| Q4.1 | Is the Instagram account Business or Creator? | `owp.metrics.instagram` | Graph API insights require one. If the account is personal, component 4 cannot be built as specified and the fallback is manual entry. Answerable immediately, and it gates all of component 4. |
| Q2.6 | Which models are permitted on GCP; are third-party tools acceptable? | `owp.script.llm_writer` | Selected via `OWP_LLM_PROVIDER`, so it stays a config change — but Gemini vs Claude changes prompt shape. |
| Q3.2 | Notification channel: Firebase push, SMS, email, Telegram, Slack, Google Chat | `owp.schedule.notifier` | Not interchangeable in effort — push needs a companion app shipped to one phone; Telegram is an afternoon. |
| Q1.10 | robots.txt and per-site ToS review | `owp.acquisition.http_fetcher` | The fetcher defaults to `respect_robots=True`; confirm that is the policy before crawling 40 sites. |
| Q2.5 | Voiceover: synthetic, Antonio's own voice, or captions only | `owp.voice` | "Captions only" deletes the stage; "own voice" makes it a file-import step. `Pipeline.produce` already accepts `tts=None`. |
| Q4.2 | The single primary objective metric | optimizer (not scaffolded) | An optimizer without a stated objective would just encode a guess. Deliberately not written. |

## Shaping — answers change behaviour, not structure

| Q | Question | Affects |
|---|---|---|
| Q1.1 | Do cross-category duplicates count toward 40, or get replaced? | `CuratedTargetSource.shortfall` |
| Q1.2 | Popularity by which measure, and which market? | target list membership |
| Q1.3 | Sensor Tower license, or curated list for the MVP? | A second `TargetSource` impl; curated is the default so this does not block |
| Q1.4 | Which of a company's policies are in scope? | `PolicyKind`; `fetch` returns a list |
| Q1.5 | US only, or EU versions too? | `Jurisdiction` |
| Q1.6 | One-time snapshot, or re-crawls with change detection? | `content_hash` exists for this |
| Q1.7 | Manual upload as a fallback for failed extraction? | `PolicySnapshot.extracted_manually` |
| Q1.8 | Store raw HTML, cleaned text, or both? | Model keeps both |
| Q1.9 | English only? | `PolicySnapshot.language` |
| Q2.1 | Which narrative formats are in scope? | `NarrativeFormat` — currently all five |
| Q2.2 | One video per policy, or several? | `ScriptWriter.write` returns one; call repeatedly |
| Q2.3 | Target length (15–90s)? | `target_seconds`, default 45 |
| Q2.7 | Accuracy bar; personal review before scheduling? | Assumed strict — see `verify_citations` and the review gate in `Pipeline.produce` |
| Q2.8 | May videos name companies and show logos/UI? | Prompt in `_build_prompt` |
| Q2.9 | Tone guardrails | Prompt in `_build_prompt` |
| Q2.10 | Per-video cost budget and weekly volume | Provider choice |
| Q3.1 | Cadence; fixed slots or optimizer-chosen | `Scheduler.schedule` |
| Q3.3 | What the link opens: download, signed URL, or a page | `Notifier.notify` |
| Q3.4 | Generate caption, hashtags, cover frame? | `ScheduledPost.caption/hashtags`, `Video.cover_frame_path` |
| Q3.5 | Expiring authenticated links, or unguessable URL? | `Notifier` auth story |
| Q3.6 | Missed slot: re-notify, roll, or skip | `PostState.MISSED` |
| Q3.7 | Approval queue before scheduling? | `PostState.APPROVED` |
| Q3.8 | How the system learns a post went live | `ScheduledPost.posted_at`, `instagram_url` |
| Q3.9 | Time zone; quiet hours | `scheduled_for` |
| Q3.10 | Notify on pipeline failures / low inventory? | `Notifier` |
| Q4.3 | Pull windows (1h / 24h / 7d) and which scores | `MetricsWindow` |
| Q4.4 | Which variables the optimizer may change | optimizer |
| Q4.5 | Automated bandit, or dashboard informing manual choices | optimizer |
| Q4.6 | Are accuracy and tone hard constraints? | Code assumes **yes** — accuracy raises rather than scores |
| Q4.7 | Looker Studio, weekly summary, or both | reporting |
| Q4.8 | Capture and analyze comments? | `PostMetrics.comments` is a count only |
| Q4.9 | Posts needed before optimization is meaningful | optimizer |
| Q4.10 | Retention and privacy constraints on commenter data | storage |

## Assumptions the scaffold makes

Where the code had to assume something, it assumed the strict reading. Each is
cheap to relax if the answer differs:

1. **Every factual claim carries a verbatim quote** (Q2.7, Q4.6) —
   `verify_citations` raises on a quote absent from the snapshot.
2. **Nothing renders unreviewed** (Q2.7) — `Pipeline.produce` raises unless
   `script.reviewed`.
3. **Captions are mandatory** — social video is watched muted.
4. **Vertical 1080×1920.**
5. **Snapshots are append-only** (Q1.6) — keeps change detection possible even
   if the MVP only ever takes one snapshot.
