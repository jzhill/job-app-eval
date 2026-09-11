# Design: Agentic Job-Application Drafting & Evaluation Pipeline

**Goal:** produce the strongest possible application — CV + written
answers — for a specific job posting, maximizing the probability of
being screened in.

Runs as a live Claude Code session, not a batch script. v1 is
single-application/flat (§3).

- Exact JSON/file shapes: [`data_schemas.md`](data_schemas.md)
- Decision history and rationale: [`history_and_rationale.md`](history_and_rationale.md)
- Open issues: [`backlog.md`](backlog.md)

---

## 1. Core principle

Score everything against the job description, not a generic rubric. The
JD is decomposed once (Stage 1) into labeled components; every downstream
score ties back to one or more of them.

Only Stage 13 (the judge panel) runs isolated from the drafting
conversation — its value depends on the executor not having produced
what it's judging. Every other stage runs directly in this session, with
full context and the ability to ask a clarifying question.

The applicant checkpoints at three points: approving context mapping
(Stage 7), the reflective interview (Stage 8), and the sniff check +
direction after each round (Stage 15). The agent drafts and prepares; a
naive panel scores; neither decides alone.

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

Only Stage 13 is a separate script (`scripts/run_judges.py`, sharing
`_common.py` with `scripts/aggregate.py`). Every other stage runs as
direct agent reasoning — resumable at any stage in a fresh conversation.

### Phase 1 — Process the job post (Stages 1–4)

Derived purely from the job posting, before any personal material enters.

#### Stage 1 — JD Decomposition
`input/job_posting.md` (pasted verbatim) → itemize → `output/jd_itemised.md`
→ **applicant verifies against the live posting** → decompose into four
categories (required qualifications, preferred qualifications, core
responsibilities, mission signals), each item with a short id →
`output/jd_components.json`, **reviewed/hand-edited by the applicant**.
Schema: [`data_schemas.md`](data_schemas.md#jd_componentsjson).

#### Stage 2 — Form Decomposition
Usually the same posting (ATS form fields on the same page). Itemize →
`output/form_itemised.md` → **applicant verifies** → structural facts
only (id, exact prompt text, limit, required) →
`output/form_questions.json`. No JD-component mapping yet — that happens
at Stage 12. Schema: [`data_schemas.md`](data_schemas.md#form_questionsjson).

#### Stage 3 — Marking Guide Co-Creation
Co-created live with the applicant → `output/marking_guide.md`: a 1–5
score-anchor rubric per component/question/CV, a per-section ≤40-word
synopsis requirement, an id-verbatim instruction, a rule connecting the
0–100 `vibe_score` to `overall_outcome`, and comment-length caps (≤40
words per component/question/CV/section comment, ≤100 words for each
overall text field). Required by `run_judges.py` — Stage 13 fails loudly
without it. Expected sections: [`data_schemas.md`](data_schemas.md#marking_guidemd).

#### Stage 4 — Drafting Guide Co-Creation
Co-created live with the applicant → `output/drafting_guide.md`: each
form question's distinct content boundary, a whole-variant cohesion
requirement (every answer + the CV reads as one coordinated case), and a
consistency check — no essay claim about the applicant's own experience
may exceed what `cv_tailored.md`/`tagged_context.json` support. Read by
every Stage 12 drafting fork alongside `voice_profile.md`. Expected
sections: [`data_schemas.md`](data_schemas.md#drafting_guidemd).

### Phase 2 — Import personal context (Stages 5–11)

#### Stage 5 — Essay Response Capture
The applicant free-writes into `input/essay/` — any number of files, any
filename, unstructured. Mapping happens at Stage 7.

#### Stage 6 — External Reference Ingestion *(optional)*
Agent digests `input/external_resources.md` (URLs) / `input/external_refs/`
(files) → `output/external_references.md`: source, summary, why flagged.
Grounding about the employer only — never usable to support a personal
claim (Stage 11).

#### Stage 7 — Context Mapping
Maps every essay fragment + external reference onto JD components/form
questions, tagging confidence and `origin`
(`essay_response`/`interview`/`external_reference`) →
`output/tagged_context.json` (+ `.md` rendering). **Checkpoint** — the
applicant approves or corrects, low-confidence fragments flagged first.
Only `essay_response`/interview-derived fragments can support a CV claim
(Stage 11); `external_reference` fragments never can. Schema:
[`data_schemas.md`](data_schemas.md#tagged_contextjson).

#### Stage 8 — Reflective Interview
Always runs, every round. Agent generates a portable brief
(`output/interview_brief.md`); the conversation itself happens in an
external voice-mode app (Claude Code has no voice interface). The
applicant drops the transcript into `input/interview_transcripts/`; agent
ingests → `output/interview_report.md`, with a separated verbatim-quotes
section for direct reuse in drafting. Quotes reused as a Stage 10 voice
sample still need the same light grammar pass as any other sample.

#### Stage 9 — Preferences File
The applicant writes `input/preferences.md` directly — how to weight
things, durable across rounds. Per-round tactical notes go in Stage 15's
`direction.md` instead.

#### Stage 10 — Voice Profiling *(optional, needs at least one proofread source)*
One-shot distillation from corrected/proofread source text only, never
raw dictated/transcribed originals → `output/voice_profile.md`, a fixed
input to every Stage 12 call. Source is normally `input/past_drafts/`,
but `input/essay/` content counts too if already proofread — proofread
status is the criterion, not folder location. Ask the applicant if
unclear.

#### Stage 11 — CV Tailoring
Reconciles every file in `input/cv/` against JD components + tagged
context + preferences → `output/cv_tailored.md` (reordered/re-emphasized,
same structure as the source) + `output/cv_tailoring_notes.json` (change
log + a `claims_checklist` tracing every claim to a source fragment,
each scored 1–5 for risk of overstating it). Single-pass, not a variant
tournament — CVs are factual/structured, lower voice-sensitivity than an
essay. Schema: [`data_schemas.md`](data_schemas.md#cv_tailoring_notesjson).

### Phase 3 — Draft variations (Stage 12)

#### Stage 12 — Draft Generation
**Input:** everything from Phases 1–2, plus the round's
`output/rounds/genN/round_config.json`. Generalized to N questions — each
variant is one coherent bundle of answers across *all* questions, drafted
together so they don't repeat each other.

- **Exploration mode** — the applicant and agent agree on 3–4 genuinely
  distinct strategic/rhetorical axes (§4), grounded in what's actually
  distinctive in the material. Each variant is drafted by its own
  **forked subagent** — full context bundle plus its one axis, no
  visibility into other forks' output. Feeds Stage 13.
- **Convergence mode** — one directed rewrite, done collaboratively
  in-conversation, incorporating the prior round's direction and retained
  phrases. No fork, no panel.
- **Comparison mode** — variants share one converged base but differ in
  production method (carried forward unmodified, hand edit, external
  tool, fresh regeneration). Non-generated variants are assembled
  directly in `output/drafts/genN/`. Judge-panelled like exploration mode
  (Stage 13's gate is simply "not convergence").

**Output:** one file per variant, `output/drafts/genN/<variant_id>.md` —
every question's answer in one document, each under a heading tagged
with its question id (`## [q<question_id>] <prompt>`). Alongside it,
`output/drafts/genN/<variant_id>.meta.json` (rationale, drafting model —
Stage 13 needs at least one judge on a different model, plus, for
comparison-mode variants, `production_method` and `derived_from`). No
per-variant folder. `variant_id` is the filename stem, any string (`v01`,
or a lineage id like `r3v1-jh`) — nothing downstream assumes a `vNN`
pattern. Every variant must pass Stage 13's submission-readiness check
before judging.

### Phase 4 — Naive HR screening (Stage 13)

#### Stage 13 — Judge Panel Evaluation
**Precondition:** submission-readiness check — `cv_tailored.md` and every
drafted variant must have no placeholder tokens, no leftover internal
notes, no near-duplicate content between a variant's own answers.
Checklist: [`CLAUDE.md`](../CLAUDE.md#submission-ready-checklist).

Runs in exploration and comparison modes; skipped for convergence.
`python scripts/run_judges.py --gen N` — the pipeline's one scripted,
isolated API call. (Variant, judge) calls run concurrently (bounded
thread pool) via `_common.py`'s streaming `call()` helper. 3–5 judges,
varied persona, at least one on a different model than the generator.
Judges see the full `input/job_posting.md` text alongside
`jd_components.json`. Each judge scores the whole package once (not
per-question): every required/preferred qualification and
core-responsibility item, a synopsis per section, every form question,
the CV, and an independent holistic `vibe_score`/outcome/two overall
comments — per `output/marking_guide.md` (Stage 3). `mission_signals` and
voice/style are not scored here. Written to
`output/evals/genN/vXX_<judge>.json`. Schema:
[`data_schemas.md`](data_schemas.md#judge-record).

### Phase 5 — Aggregate & understand outcome (Stages 14–15)

#### Stage 14 — Aggregation
`python scripts/aggregate.py --gen N` computes the deterministic numeric
rollup — mean/variance per component per variant, a section-level
rollup, per-question rollups, CV-evaluation consensus — into
`output/evals/genN/summary.json`. Agent reads every judge file directly
and writes the qualitative synthesis into `summary.md`: top 2–3 variants,
plus comments recurring across ≥2 judges.

#### Stage 15 — Human Sniff Check + Direction Capture
The applicant reads the top 2–3 variants and `summary.md` directly before
anything regenerates. Produces `output/rounds/genN/direction.md`:
commentary, explicitly retained/dropped phrases, and the mode choice for
the next round.

### Phase 6 — Iterate (Stage 16)

#### Stage 16 — Directed Iteration
Not a fully automatic mutation loop. Agent reads `direction.md` +
`summary.md` + `preferences.md` → `output/rounds/gen(N+1)/round_config.json`
(finalized mode + variant count, pointer to the direction file, retain/
drop lists). Schema: [`data_schemas.md`](data_schemas.md#round_configjson).
The applicant approves or adjusts; the cycle loops back to Phase 3 (or
Phase 2, if new context is needed first).

---

## 3. Repo structure

Single-application/flat — no `applications/<slug>/` scaffolding yet.

```
repo/
├── input/                        # gitignored — human-provided material
│   ├── job_posting.md            # required — pasted verbatim by the applicant
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
both gitignored — draft text, judge scores, and the tailored CV are the
application's actual substance and strategy, not a repackaging of public
information.

`preferences.md` lives in `input/`, not `output/` — human-authored, not
agent-generated.

---

## 4. Variant count and round mode

Default **3–4 variants** for a first exploration round; widen to 5–10
only if a round's `summary.md` shows scores bunched close together
across many variants.

Each round is explicitly one of three modes, chosen by the applicant at
Stage 15: exploration (variant tournament + judge panel), convergence
(single refined draft, no panel), or comparison (shared base, differing
production method, also judge-panelled — see Stage 12).
