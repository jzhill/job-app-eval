# Design: Agentic Job-Application Drafting & Evaluation Pipeline

**Goal:** produce the strongest possible application — CV + written
answers — for a specific job posting, and maximize the probability of
being screened in. Everything below serves that one goal; nothing here
is an end in itself.

A small repo, operated as a live Claude Code session, not a batch script.
v1 stays single-application/flat (see §3) — the generalization beyond one
application is in the pipeline's shape, not yet in the folder structure.

Exact JSON/file shapes for every generated artifact live in
[`data_schemas.md`](data_schemas.md), not here. Full decision history and
the reasoning behind anything not obvious from this doc lives in
[`history_and_rationale.md`](history_and_rationale.md) — this document
states *what the pipeline does*; that one explains *why it ended up this
way*.

---

## 1. Core principle

Score everything against the job description, not a generic rubric — the
JD is decomposed once (Stage 1) into labeled components, and every
downstream score, human or judge, ties back to one or more of them.

Naivety is scarce: only Stage 13 (the judge panel) needs to be blind to
how the material was produced — it's the only stage whose value depends
on the executor not having been part of the conversation that produced
what it's judging. Every other stage runs directly in this Claude Code
session, in conversation with Jeremy, because those stages benefit from
full context and the ability to ask a question instead of guessing. (Why
the line falls exactly there, not somewhere else:
[`history_and_rationale.md`](history_and_rationale.md#naivety-vs-context).)

Jeremy stays in the loop at three points by design: approving context
mapping (Stage 7), participating directly in the reflective interview
(Stage 8), and doing the sniff check + giving direction after each round
(Stage 15). The agent drafts and prepares; a naive panel scores; neither
decides alone.

---

## 2. Pipeline — six phases

```
Phase 1 — Process the job post        Stages 1–4
Phase 2 — Import personal context     Stages 5–11
Phase 3 — Draft variations            Stage 12
Phase 4 — Naive HR screening          Stage 13
Phase 5 — Aggregate & understand      Stages 14–15
Phase 6 — Iterate                     Stage 16   → back to Phase 2 or 3
```

Only Stage 13 is a separate script (`scripts/run_judges.py`, plus the
`_common.py` Anthropic SDK helper it shares with `scripts/aggregate.py`).
Every other stage is executed by the Claude Code agent directly, so the
pipeline can be picked up at any stage in a fresh conversation.

### Phase 1 — Process the job post (Stages 1–4)

All four stages here derive purely from the job posting, before any of
Jeremy's personal material enters the picture.

#### Stage 1 — JD Decomposition
**Input:** `input/job_posting.md` (Jeremy pastes the raw posting text).
Itemize → `output/jd_itemised.md` → **Jeremy verifies against the live
posting** → decompose into four categories (required qualifications,
preferred qualifications, core responsibilities, mission signals), each
item keeping a short id → `output/jd_components.json`, **reviewed/
hand-edited by Jeremy**. Schema: [`data_schemas.md`](data_schemas.md#jd_componentsjson).

#### Stage 2 — Form Decomposition
**Input:** usually the same posting (form fields are typically on the
same ATS page). Itemize → `output/form_itemised.md` → **Jeremy verifies**
→ purely structural facts (id, exact prompt text, limit, required) →
`output/form_questions.json` — deliberately doesn't pre-assign JD
components to a question; that mapping happens at Stage 12. Schema:
[`data_schemas.md`](data_schemas.md#form_questionsjson).

#### Stage 3 — Marking Guide Co-Creation
**Input:** Stages 1–2's outputs. Co-created live with Jeremy (same
checkpoint style as Stage 7) → `output/marking_guide.md`: a general 1–5
score-anchor rubric for required/preferred qualifications, core
responsibilities, questions, and the CV (`mission_signals` items are
context only, not scored individually), a per-section ≤40-word
qualitative synopsis requirement, an instruction to use ids verbatim, a
rule connecting the independent holistic 0–100 `vibe_score` to
`overall_outcome`, and a comment-length cap (≤40 words per component/
question/CV/section comment, ≤100 words each for the two overall text
fields — a starting default, not fixed). `scripts/run_judges.py` requires
this file to exist and splices it into the judge system prompt — a hard
precondition for Stage 13, not an optional nicety. Expected sections:
[`data_schemas.md`](data_schemas.md#marking_guidemd).

#### Stage 4 — Drafting Guide Co-Creation
**Input:** same as Stage 3. Co-created live with Jeremy →
`output/drafting_guide.md`: each form question's distinct content
boundary against the others, a whole-variant cohesion requirement (every
answer + the CV reads as one coordinated case), and the consistency check
that any claim about Jeremy's own experience must not exceed what
`cv_tailored.md`/`tagged_context.json` support. This is the essay side of
the pipeline's overclaim guard (§5). Read by every Stage 12 drafting fork
alongside `voice_profile.md`. Expected sections:
[`data_schemas.md`](data_schemas.md#drafting_guidemd).

### Phase 2 — Import personal context (Stages 5–11)

#### Stage 5 — Essay Response Capture
Jeremy free-writes into `input/essay/` — any number of files, any
filename, fully unstructured. No mapping required of him; that's Stage
7's job.

#### Stage 6 — External Reference Ingestion *(optional)*
Agent digests `input/external_resources.md` (URLs) / `input/external_refs/`
(files) → `output/external_references.md`: source, summary, why flagged.
Grounding/color about the employer — never treated as a claim about
Jeremy (the overclaim guard applies only to claims about him).

#### Stage 7 — Context Mapping
Maps every essay fragment + external reference onto JD components/form
questions, tagging confidence and `origin`
(`essay_response`/`interview`/`external_reference`) →
`output/tagged_context.json` (+ `.md` rendering for review). **Jeremy
checkpoint** — approves or corrects, low-confidence fragments flagged
first. `origin` matters: only `essay_response`/interview-derived
fragments can support a CV claim about Jeremy (Stage 11) — an
`external_reference` fragment never can. Schema:
[`data_schemas.md`](data_schemas.md#tagged_contextjson).

#### Stage 8 — Reflective Interview
Always runs, every round. Agent generates a portable brief
(`output/interview_brief.md`); the actual conversation happens in an
external voice-mode app (Claude Code has no voice interface) — Jeremy has
it there, drops the transcript into `input/interview_transcripts/`, agent
ingests → `output/interview_report.md`, with a separated verbatim-quotes
section flagged for direct reuse in drafting. Jeremy is an active
participant here, not a passive input source. Quotes reused later as a
Stage 10 voice sample still need the same light grammar pass as any other
sample first.

#### Stage 9 — Preferences File
Jeremy writes `input/preferences.md` directly — how to weight things
(not facts about him), durable across rounds. Per-round tactical notes
belong in Stage 15's `direction.md` instead, so this file doesn't
accumulate noise.

#### Stage 10 — Voice Profiling *(optional, needs at least one proofread source)*
One-shot distillation — not a loop — from corrected/proofread source
text only, never raw dictated/transcribed originals →
`output/voice_profile.md`, a fixed input to every Stage 12 call, not
regenerated per variant/round. Source is normally `input/past_drafts/`,
but `input/essay/` content counts too if it's actually already polished
for this application rather than rough freewriting — proofread status is
the real criterion, not which folder a file sits in. If it's unclear
which applies, ask Jeremy rather than assuming from folder location
alone.

#### Stage 11 — CV Tailoring
Reconciles every file in `input/cv/` against JD components + tagged
context + preferences → `output/cv_tailored.md` (reordered/re-emphasized,
same structure as the source) + `output/cv_tailoring_notes.json` (change
log + a `claims_checklist` tracing every claim to a source fragment,
each scored 1–5 for overclaim risk). Together with Stage 4's consistency
check, this is the pipeline's entire overclaim guard (§5) — deliberately
single-pass, not a variant tournament, since CVs are factual/structured
and lower voice-sensitivity than an essay. Schema:
[`data_schemas.md`](data_schemas.md#cv_tailoring_notesjson).

### Phase 3 — Draft variations (Stage 12)

#### Stage 12 — Draft Generation
**Input:** everything from Phases 1–2, plus the round's
`output/rounds/genN/round_config.json`. Generalized to N questions — each
variant is one coherent bundle of answers across *all* questions, drafted
together so they don't repeat each other.

- **Exploration mode** — Jeremy and the agent agree on a handful of
  genuinely distinct strategic/rhetorical axes for the round first (§4 —
  3–4 for a first round, more only if warranted), grounded
  in what's actually distinctive in the material, not a generic grid.
  Each variant is then drafted by its own **forked subagent** — full
  context bundle plus its one axis, no visibility into other forks' output
  — so variants stay independently-bet hypotheses rather than converging
  mid-session. Feeds Stage 13.
- **Convergence mode** — one directed rewrite, done collaboratively
  in-conversation, incorporating the prior round's direction and retained
  phrases. No fork, no panel.

**Output:** `output/drafts/genN/vXX/q<question_id>.md` + `vXX.meta.json`
(axis/rationale + which model drafted it — Stage 13 needs at least one
judge on a different model than this one, to reduce self-preference
bias). Every variant needs to pass Stage 13's submission-readiness check
before judging — see below.

### Phase 4 — Naive HR screening (Stage 13)

#### Stage 13 — Judge Panel Evaluation
**Precondition: a cheap, non-naive submission-readiness check runs
first.** Before running, the agent verifies `cv_tailored.md` and every
drafted variant are actually ready to be scored — no placeholder tokens,
no leftover internal notes/meta-commentary left in the content itself,
and no near-duplicate content between a variant's own answers. This is a
hygiene problem, not a judgment call, so it doesn't need Stage 13's
naivety to catch it — it just needs to happen before spending judge-panel
money on a defect a plain read would catch (the gen1 pilot ran an
unfilled CV placeholder through 21 judge calls before this check
existed — see `backlog.md`). Checklist: [`CLAUDE.md`](../CLAUDE.md#submission-ready-checklist).

**Only runs in exploration-mode rounds.** `python scripts/run_judges.py
--gen N` — the pipeline's one scripted, isolated Anthropic API call;
judges must never share context with the session that produced the
material they're evaluating. Every (variant, judge) call is independent,
so they run concurrently (a bounded thread pool, not one call at a time)
— this is purely a scheduling optimization within the script and doesn't
touch the isolation guarantee at all. Calls go through `_common.py`'s
`call()` helper using the Messages API's streaming mode, not a single
blocking request — these are large, high-effort generations (26 scored
components + 4 questions + CV + section assessments + two overall
comments per call) that can run long enough to trip the SDK's non-
streaming request-duration limit otherwise. 3–5 judges, varied persona, at
least one on a different model than the generator. Judges see the full
`input/job_posting.md` text alongside its structured `jd_components.json`
breakdown — a real screener reads the posting itself, not just a
checklist derived from it. Each judge scores the whole package **once**
(not per-question): every required/preferred
qualification and core-responsibility item, a qualitative synopsis per
section, every form question, the CV, and an independent holistic
`vibe_score`/outcome/two overall comments — all per the rubric in
`output/marking_guide.md` (Stage 3). `mission_signals` and voice/style are
deliberately not scored here — style is Stage 4/12's job, not a naive HR
screener's. Written to `output/evals/genN/vXX_<judge>.json`. Schema:
[`data_schemas.md`](data_schemas.md#judge-record).

### Phase 5 — Aggregate & understand outcome (Stages 14–15)

#### Stage 14 — Aggregation
`python scripts/aggregate.py --gen N` computes the deterministic numeric
rollup — mean/variance per component per variant, a section-level rollup
(by the three scored JD categories), per-question rollups, CV-evaluation
consensus — into `output/evals/genN/summary.json`. Agent then reads every
judge file directly and writes the qualitative synthesis into
`summary.md`: top 2–3 variants, plus whichever comments recur across ≥2
judges (the score says *that* something's wrong, the recurring comment
says *what*).

#### Stage 15 — Human Sniff Check + Direction Capture
Jeremy reads the top 2–3 variants and `summary.md` himself before
anything regenerates — the ground-truth check a synthetic panel can't do
alone. Produces `output/rounds/genN/direction.md`: freeform commentary,
explicitly retained/dropped phrases, and his choice of mode for the next
round.

### Phase 6 — Iterate (Stage 16)

#### Stage 16 — Directed Iteration
Not a fully automatic mutation loop. Agent reads `direction.md` +
`summary.md` + `preferences.md` → `output/rounds/gen(N+1)/round_config.json`
(finalized mode + variant count, pointer to the direction file, explicit
retain/drop lists). Schema:
[`data_schemas.md`](data_schemas.md#round_configjson). Jeremy approves or
adjusts, then the cycle loops back to Phase 3 (or Phase 2, if the
direction calls for gathering new context first).

---

## 3. Repo structure

Single-application/flat for now — no `applications/<slug>/` scaffolding
yet. (A durable, cross-application "experience bank" for facts that
surface mid-run is a stray future idea, not an active plan — revisit only
once a second real application exists to show what's actually worth
sharing vs. per-application.)

```
repo/
├── input/                        # gitignored — human-provided material
│   ├── job_posting.md            # required — pasted verbatim by Jeremy
│   ├── cv/                       # required — one or more CV versions, any format/filename
│   ├── essay/                    # required — one or more free-written content files
│   ├── preferences.md            # optional — how to weight things, human-authored
│   ├── external_resources.md     # optional — list of URLs, one per line
│   ├── external_refs/            # optional — raw files (PDFs etc.)
│   ├── interview_transcripts/    # optional — transcripts/notes from any live interview session
│   └── past_drafts/              # optional — corrected writing samples for voice profiling only
├── output/                       # gitignored — everything the pipeline generates
│   ├── jd_itemised.md / jd_components.json
│   ├── form_itemised.md / form_questions.json
│   ├── marking_guide.md / drafting_guide.md
│   ├── external_references.md
│   ├── tagged_context.json / tagged_context.md
│   ├── interview_brief.md / interview_report.md
│   ├── voice_profile.md
│   ├── cv_tailored.md / cv_tailoring_notes.json
│   ├── drafts/genN/vXX/q<question_id>.md + vXX.meta.json
│   ├── evals/genN/vXX_<judge>.json + summary.json + summary.md
│   └── rounds/genN/direction.md, gen(N+1)/round_config.json
├── scripts/                      # committed
│   ├── _common.py                 # Anthropic SDK helper
│   ├── run_judges.py              # Stage 13 — the only stage that calls the Anthropic API
│   ├── aggregate.py               # Stage 14 — deterministic numeric rollup, no API key needed
│   └── deprecated/                # superseded per-stage scripts, kept for reference only
├── .claude/skills/run-cycle/SKILL.md   # guided end-to-end sequencing
├── design/                       # this doc, data_schemas.md, history_and_rationale.md, backlog.md
├── README.md
└── .gitignore
```

**Only code and documentation are public.** `input/` and `output/` are
both gitignored, full stop — draft text, judge scores, and the tailored
CV are the application's actual substance and strategy, not a
repackaging of public information. See README.md ("Background").

`preferences.md` lives in `input/`, not `output/`, despite being a named
stage (9) — it's human-authored, like `input/essay/`, not agent-generated.

---

## 4. Variant count and round mode

Default **3–4 variants** for a *first* exploration round — narrower than
the 5–10 ceiling, since gen1 defaulted to 7 and 6 of those 7 landed
statistically indistinguishable on overall score, evidence that the top
of the range doesn't reliably buy more signal. Each round is explicitly
either exploration (variant tournament + judge panel) or convergence
(single refined draft, no panel), chosen by Jeremy at Stage 15.

Widen (up to 5–10) only if a round's `summary.md` shows scores bunched
close together across many variants (the axes picked aren't
discriminating) — that's the signal to add more axes/variants, not a
default starting assumption.

---

## 5. Overclaim guard, and where to find the rest of the story

A real overclaim slipped through several drafting rounds in the original
manual pilot before an independent read caught it (README "Background").
The guard today is two plain checks, not a scored judge dimension: Stage
11's `claims_checklist` for the CV, and Stage 4's drafting-guide
consistency instruction for the essay. Both trace claims about Jeremy
back to source fragments and refuse to let a draft exceed what those
fragments support.

That's the one piece of "why" load-bearing enough to restate here. For
everything else — the naivety/context split's full reasoning, this
guard's evolution across versions of the design, why Stages 1–2 use
direct paste + itemize/verify instead of automated fetch, why voice
profiling is one-shot, why the public/private line is drawn where it is,
and the ongoing retrospective of what's actually been learned running
this pipeline for real — see
[`history_and_rationale.md`](history_and_rationale.md) and
[`backlog.md`](backlog.md).
