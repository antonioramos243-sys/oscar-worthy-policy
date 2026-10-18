# Requirements decisions

Source of record: the "Privacy Policy Videos MVP: Requirements Questions"
Google Doc, answered in comments. This file records what was decided, where it
is enforced in code, and the four places the answers still leave a gap.

All 40 questions are answered. **Q2.1 was answered 2026-10-17**, by the owner,
in conversation rather than in the doc: every video is the covered company's own
CEO speaking to the viewer, explaining what agreeing to their privacy policy
lets them do with the viewer's data. See "The Q2.1 answer" below — it is the
decision with the widest blast radius so far.

## Carried over as already decided

40 policies (10 social, 10 dating, 5 AI, 15 top apps) · GCP · Instagram only,
posted manually · phone notification at posting time.

## 1. Policy acquisition

| Q | Decision | Where |
|---|---|---|
| 1.1 | Cross-category duplicates are replaced by the next-ranked entry | `CuratedTargetSource` raises `DuplicateTargetError` |
| 1.2 | Ranked by monthly active users (or similar) | `Target.rank` |
| 1.3 | No Sensor Tower license; rank once when building the index, no API integration. Consider alternatives if Sensor Tower is not possible | `CuratedTargetSource` is the only implementation |
| 1.4 | US policy of the ranked product; main + cookie + others **merged into one document**, to tell a cohesive story | `PolicyCorpus`, `merge_documents`, `HttpPolicyFetcher.fetch` |
| 1.5 | US only | `PolicyCorpus`; `Accept-Language: en-US` in `DEFAULT_HEADERS` |
| 1.6 | One-time snapshot; no re-crawls | No version history on `PolicyCorpus`; `owp.acquisition.store` keys a file by slug alone |
| 1.7 | Manual upload is an acceptable fallback | `corpus_from_text`, `owp fetch --paste`, `PolicySource.extracted_manually` |
| 1.8 | Cleaned text only — raw HTML is not retained | `owp.acquisition.clean`; `PolicyCorpus.text`; `raw_html` removed |
| 1.9 | English only | `PolicyCorpus.text` |
| 1.10 | No legal constraints to observe | `HttpPolicyFetcher(respect_robots=False)`, honoured when set |

On 1.10: recorded as answered. The flag is kept because privacy-policy pages are
almost always crawl-allowed, so honouring robots.txt would likely cost no
coverage if that is ever revisited. It is implemented rather than merely
accepted, so turning it on does what it says.

Two judgement calls the answers did not cover, both made so that a silent
failure is impossible. A document that cannot be extracted does not fail its
target — a company that has moved its cookie policy still yields a corpus from
its main policy — but a page under `MIN_POLICY_CHARS` of text counts as no
text at all, because a consent wall and a page that renders itself in the
browser both answer 200 with an almost empty body, and a video written from
that would misrepresent a policy nobody read (Q2.7).

## 2. Narrative video generation

| Q | Decision | Where |
|---|---|---|
| 2.1 | **Answered 2026-10-17**: the company's CEO, to camera, on what agreeing permits | `NarrativeFormat.CEO_DIRECT_ADDRESS`, `verify_attribution` |
| 2.2 | Several videos per policy, each on one practice | `Script.practice`, `ScriptWriter.practices` |
| 2.3 | 30–90 seconds | `LengthBucket` |
| 2.4 | Animation, characters consistent **across** videos. Cast decided 2026-10-17: the CEOs of the covered companies | `owp.cast`, `verify_cast`, `HybridRenderer` |
| 2.5 | Synthetic voice | `owp.voice` |
| 2.6 | Any model, balancing cost / engineering overhead / quality. A perceived quality score is applied per video and may block posting; dimensions include animation quality, character and narrative consistency, storyline quality | `QualityScore`, `Pipeline.record_review` |
| 2.7 | Citations not required — personal review covers accuracy — but videos must not misrepresent the policy. **Superseded for CEO lines**: see below | `verify_quotes`; `verify_attribution` requires a citation per real-person line |
| 2.8 | Name the company and use its logo | prompt, `LlmScriptWriter` |
| 2.9 | Optimize for engaging, shareable videos | `owp.optimize` |
| 2.10 | **Weekly operational cost ≤ $25 — confirmed firm** | `owp.budget`, enforced in `Pipeline.produce` |

### The Q2.1 answer: the CEO addresses the viewer

**Decided 2026-10-17.** Each video is the CEO of the company whose policy it
covers, speaking to the viewer, explaining what the viewer's agreement permits.
Three things follow, and two of them are constraints rather than features.

**The format stops being a variable.** `NarrativeFormat` holds one member, so
the arm space falls from 675 to 135 (`all_arms`) and the bandit no longer spends
observations on formats nobody wants. The enum is kept rather than collapsed, so
adding a second format re-opens the variable with no other change, and a
variable slot is now free under Q4.4's cap of about five.

**Citations stop being optional — for the CEO.** Q2.7 made them optional because
every video gets a personal review, and that reasoning held while the cast was
invented characters: the worst case was being wrong about a company. It does not
hold now. A line in a video where a named, recognisable person says "I can sell
what you looked at" is a statement attributed to that individual, and a reviewer
reading a fluent script is exactly who will not notice that the policy never
said it. So `verify_attribution` refuses to pass a script in which a
`real_person` character speaks an uncited line, and `verify_quotes` then proves
the citation is verbatim in the corpus. Together: in a video, a real person only
ever says something their own policy says. An invented character still falls
back to Q2.7.

**The depiction must not be able to pass as real.** This is the one risk the
format creates that no gate in the pipeline can catch, so it is recorded as a
constraint on the render and voice stages rather than left implied:

- Flat 2D caricature, never photorealistic. Each real person's `appearance` in
  `cast.json` says so, and a test enforces that it says so.
- A plainly synthetic off-the-shelf TTS voice, never a clone of the person's
  own. Also tested.
- The render and the generated caption (Q3.4) should carry a visible
  commentary/satire marker. Not yet enforced — the render stage is a stub, and
  this is the first thing to wire into it.

**Who the CEO is, is a fact with a shelf life.** A video in which last quarter's
CEO explains this quarter's policy is wrong about a named person, and review will
not catch it because the face looks right. So each real person in `cast.json`
carries `verified_on` and `source`, both required by test. The four currently
listed were checked on 2026-10-17 against press and institutional sources;
before the first render, confirm each against the company's own leadership or
investor-relations page, which is the only primary source.

One CEO covers every target their company publishes a policy for, so the cast
stays smaller than the 40-target list and the same drawn person recurs across
all of a company's videos — which is a better answer to Q2.4's consistency
requirement than the generic cast it replaced.

### The Q2.4 / Q2.10 conflict: resolved as hybrid

**Decided 2026-10-18: hybrid rendering, and the $25/week cap is firm.**

Drawn characters composited over generated background plates. Each technique
is used where it is strong: generated video gives cheap visual variety, drawn
assets give character consistency, which is the thing generative models are
worst at holding across separate generations.

The cap only permits this if plates are a **reusable library rather than a
per-video cost**. Generated per video, backgrounds cost about $12/week forever
- half the cap. Generated once and reused, the same spend is a one-off:

| Plates | Seconds | One-time cost | Share of one week's cap |
|---|---|---|---|
| 20 | 160 | $8.00 | 32% |
| 30 | 240 | $12.00 | 48% |
| 60 | 480 | $24.00 | 96% |

Reserving the $0.64 that four videos cost, **60 plates can be generated in a
single week** alongside normal output. After that, steady-state cost is TTS plus
one LLM call - about **$0.16 a video, or $0.64/week at four a week, 2.6% of the
cap**. Enforced by `PlateLibrary.affordable_batch`, which truncates a batch to
what the week affords rather than rejecting it, so the library grows weekly.

Rates are Veo 3.1 Lite 720p at $0.05/second, from third-party summaries;
confirm against Google's own pricing page before relying on them.

**Full generative rendering was rejected and is not in the codebase.** A firm
$25 cap rules out every tier above Lite, and Lite is exactly where
`animation_quality` and `character_consistency` - two of the four quality
dimensions in Q2.6 - score worst. Paying for takes that the quality score then
rejects is the worst of both.

Remaining dependency is artwork, not a decision: `cast.json` now names four real
CEOs but their appearances are briefs for an artist rather than drawn assets,
there is no `asset_dir`, and `plates.json` has four placeholder prompts. Nothing
renders until the cast is drawn.

Also unresolved: Q2.9 asks for tone guardrails and the answer describes an
optimization goal instead, while Q4.6 makes tone a hard constraint. A hard
constraint with no stated limit cannot be enforced, so `LlmScriptWriter.tone`
takes the conservative reading as an explicit parameter. This matters more since
Q2.1 was answered: the tone is now a real person's own voice, not a narrator's.

## 3. Scheduling and notification

| Q | Decision | Where |
|---|---|---|
| 3.1 | Research requested → **4 posts/week** (sources converge on 3–5) | `DEFAULT_PER_WEEK` |
| 3.2 | Whichever channel is simplest → **email** | `EmailNotifier` |
| 3.3 | A small web page with video, caption and hashtags | `EmailNotifier.review_base_url` |
| 3.4 | System generates caption, hashtags and cover frame | `ScheduledPost`, `Video.cover_frame_path` |
| 3.5 | Links require authentication | Cloud Run behind IAP, one Google account |
| 3.6 | Missed slot rolls to the next one | `PostState.ROLLED`, `Scheduler.roll` |
| 3.7 | No approval queue — straight to the schedule | No gate in `Pipeline.enqueue` |
| 3.8 | Antonio pastes the Instagram URL back | `ScheduledPost.instagram_url` |
| 3.9 | Eastern time, nothing before 09:00 or after 22:00 | `owp.schedule.slots` |
| 3.10 | Pipeline failure alerting left to GCP monitoring | out of scope |

On 3.2: email is the simplest channel that still satisfies 3.3 and 3.5 — no
companion app to ship (Firebase push), no bot to register (Telegram), no carrier
rules (SMS), and iOS already pushes mail. The authenticated page is the real
work; IAP avoids building sign-in.

Cadence sources: [Kontentino](https://www.kontentino.com/blog/how-often-to-post-on-instagram/),
[Dash Social](https://www.dashsocial.com/blog/how-often-should-you-post-on-instagram),
[Social Rails](https://socialrails.com/blog/instagram-posting-frequency-guide),
[Sendible](https://www.sendible.com/insights/best-time-to-upload-reels-on-instagram).
These are vendor blogs with overlapping claims and no primary data; Instagram
publishes no target and Mosseri has said there is no ideal number. Treat 4/week
as a starting point to test, which is why `per_week` is a parameter.

## 4. Engagement tracking and optimization

| Q | Decision | Where |
|---|---|---|
| 4.1 | Creator account — Graph API insights available | `InstagramGraphMetrics` |
| 4.2 | Objective: inform people about poor privacy practices | `informed_score` |
| 4.3 | Pull at 1h, 3h, 9h, 24h, 7d | `PULL_SCHEDULE_HOURS` |
| 4.4 | Any variables, **max ~5** | `owp.optimize.arms` — exactly 5 |
| 4.5 | Automated optimizer | `FactoredBandit` |
| 4.6 | Accuracy and tone are hard constraints | Not dimensions at all |
| 4.7 | Dashboard **and** weekly summary | `FactoredBandit.estimates` |
| 4.8 | Comments not collected yet | `PostMetrics.comments` is a count |
| 4.9 | First few weeks are pure exploration | `EXPLORATION_POSTS = 12` |
| 4.10 | Indefinite retention; no commenter data | — |

Q4.2 gives a mission, not a metric, and the bandit maximizes whatever it is
given. `informed_score` uses **reach + 10 × shares**: reach is the closest
proxy for people informed, and shares produce future reach. Views are rejected
as the objective because a view counts at a fraction of a second, so maximizing
views rewards thumb-stopping that informs nobody. The weight of 10 is a
starting point, not a finding. **Confirm this proxy** — it is the one decision
that silently redirects everything downstream.

Q4.3 names the windows but not which one scores a variant; `SCORING_WINDOW` is
24h, long enough for a Reel's first wave and short enough not to block the
bandit for a week per observation. 7d is retained for reporting.

The five variables are format, hook style, length bucket, visual style and
posting hour. Voice is excluded (settled by Q2.5, and per-character voices
belong to the cast), as are company and category — letting a bandit drop
unpopular companies would quietly defeat Q4.2. That space is 675 arms against
about four observations a week, which is why the bandit learns per variable
rather than per arm.

## Still needed

1. **Q2.1** — which narrative formats are in scope.
2. **Tone limit** — Q4.6 makes it a hard constraint; Q2.9 never set one.
3. **Confirm the objective proxy** — reach + 10 × shares for "inform people".

Resolved since the first pass: the animation approach (hybrid, above).

## Not a decision — just work

- Draw the character cast and fill in `cast.json` (`appearance`, `asset_dir`).
- Write real plate prompts in `plates.json`, then generate a first batch.
- Install ffmpeg and implement `HybridRenderer.render`.
