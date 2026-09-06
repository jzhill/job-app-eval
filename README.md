# job-app-eval

Meta-job application, with agentic evaluation. A pipeline that drafts and
evaluates job-application text (essay questions + tailored CV) against a
specific job posting, using a multi-judge LLM panel. Full design:
[`design/agentic_application_eval_design.md`](design/agentic_application_eval_design.md).

**Most of this pipeline is not a script you run — it's a conversation you
have with Claude Code in this folder.** Only the judge-panel step (Stage
11) is a separate scripted call to the Anthropic API, because that's the
one stage whose whole value depends on the judge not having seen the
conversation that produced the draft it's evaluating. Every other stage —
decomposing the job posting, tagging your material, tailoring your CV,
drafting variants — is something you ask the agent to do directly, with
full context and room to ask you a clarifying question instead of quietly
guessing. See the design doc §1 for why the pipeline splits this way.

## Background

This started as a manual pilot for one specific application (Anthropic's
Partner Manager, Global Health role): drafting a "Why this role" essay by
hand across several revisions, then running each version through a naive
LLM acting as an HR screener to see what an outside reader would flag.
Nine separate runs later, a clear, consistent pattern of findings emerged
across all of them — evidence that the naive-screener approach was
surfacing real signal, not noise from one run's phrasing.

That manual process also caught something more consequential than
polish: an early draft overstated the candidate's role in a piece of
past technical work — a mistake the writer hadn't noticed himself, and
one an LLM drafting agent could easily reintroduce during later revision
if nothing was checking for it. That near-miss is the direct reason this
pipeline treats overclaim risk as a first-class, permanent judge score
(see the design doc) rather than something to catch by eye each time — and
the direct reason the judge panel is the one stage that stays isolated
from everything else (design doc §1).

The manual process worked, but it didn't scale — nine ad hoc runs,
read and synthesized by hand, is a lot of overhead for one application,
and the whole point of doing this well is to apply what worked to future
applications too. This repo formalizes that manual workflow into a
repeatable pipeline: decompose the job posting into scoreable components,
draft against them, evaluate with a diverse judge panel instead of one
screener, and aggregate the findings automatically. There's also a
second, more pointed reason to build it well: a tool that evaluates and
improves an application for an AI safety company, built using careful,
skeptical evaluation methodology, is itself a small demonstration of the
kind of judgment the role is looking for.

## What a round of evaluation actually produces

An exploration round runs design doc §2's Stages 10–12: a set of draft
variants, each independently scored by a panel of judges, rolled up into
one readable summary.

**Drafting (Stage 10):** before anything gets written, you and the agent
agree on a handful of genuinely distinct angles for the round — real
strategic bets grounded in your actual material (one variant leading with
a specific argument, another with a specific story), not a generic
structural grid. Each variant is then drafted by its own forked subagent,
independently — it never sees what the other variants say — so the bets
stay genuinely distinct instead of converging toward whatever the
conversation happens to settle on.

**Judging (Stage 11):** the one step that runs as a separate, scripted
call to the Anthropic API (`scripts/run_judges.py`), deliberately isolated
from the conversation that produced the drafts — that isolation is the
whole point (see above). A panel of judges with different personas, at
least one on a different model than whatever drafted the variants, each
scores the *entire application package* — every question's answer plus the
tailored CV together, not each question in isolation, because a real
reader forms one impression of the whole thing, not several. Every JD
component and every form question gets its own score and comment, plus one
overall score/outcome and a low-weight style-fidelity check kept separate
from content scoring.

**What comes back (Stage 12):** `output/evals/genN/summary.json` — a
deterministic numeric rollup (mean/variance per JD component per variant,
plus a section-level and per-question rollup, no API call involved) — and
`output/evals/genN/summary.md`, the file actually worth reading: the
top-ranked variants, plus whichever comments recur across two or more
judges — the numeric score says *something's* wrong, the recurring comment
says *what*. Exact file shapes:
[`data_schemas.md`](design/data_schemas.md#judge-record).

That's what you read at the sniff-check (design doc §Stage 13) before
directing the next round.

## Setup

1. `python -m venv .venv` then `.venv/Scripts/activate` (Windows) or
   `source .venv/bin/activate` (Mac/Linux), then
   `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and fill in your key from
   console.anthropic.com: `ANTHROPIC_API_KEY=sk-ant-...`. `.env` is
   gitignored and loaded automatically by every script under `scripts/`
   (including `scripts/deprecated/`, kept for reference — see design doc
   §3) — never commit it, never put the key anywhere else in the repo.
   Only `scripts/run_judges.py` actually needs the key at runtime; nothing
   else in the active pipeline does, since everything besides Stage 11
   runs as the Claude Code agent's own reasoning in this session, not a
   separate API call.
3. Only code and documentation are public here. `input/` and `output/`
   are both gitignored, full stop — nothing in either gets committed.
   `input/` is what you provide; `output/` is everything the pipeline
   generates from it. Draft text and judge scores are the application's
   actual substance, not just a repackaging of public information, so
   none of it belongs in a public repo.

## Required inputs (place in `input/`)

| File/folder | What it is |
|---|---|
| `job_posting.md` | Copy-paste the **raw text of the job posting**, straight from the browser. If the application form's fields are on the same page (common on Greenhouse and similar ATS platforms), paste those too — one file covers both. |
| `cv/` | Drop in one or more CV versions — a generic one, a version already partly tailored for a similar role, whatever you have. Any format (`.docx`/`.pdf`/`.md`), any filename — the agent reconciles across them when tailoring (Stage 9). |
| `essay/` | Write freely — one or more files, any filename. Your own words on why this role, relevant experience, motivation. No structure required, no need to address specific requirements one by one; just write toward the posting loosely. The pipeline maps this onto the posting's actual requirements for you. |

## Optional inputs (also in `input/`)

| File/folder | What it is |
|---|---|
| `preferences.md` | How you want the pipeline to weight things — not facts about you, priorities (e.g. "prioritize argument X", hard constraints that must never be reverted). |
| `external_resources.md` | A list of URLs (articles, org pages, reports) you find relevant background, one per line, with an optional note on why. |
| `external_refs/` | Any files (PDFs etc.) that serve the same purpose. |
| `interview_transcripts/` | Transcripts or notes from a live interview conversation (Stage 6) — one you already had on your own initiative, or one prompted by a brief the agent generated. Any filename; drop in more as follow-up rounds happen. |
| `past_drafts/` | Prior application drafts, if you have any — **corrected/proofread text only** — used to build a voice profile of your writing style (Stage 8). Kept separate from `essay/` on purpose: that folder is expected to hold rough freewriting, and mixing the two risks feeding uncorrected prose into the voice profile. |

Everything the pipeline generates lands in `output/`, mirroring this same
gitignored treatment — see the design doc §3 for the full layout.

## Usage

There are two ways to run this: **guided** (recommended — a `/run-cycle`
skill walks the whole thing for you) or **manual** (asking for one stage
at a time — useful for redoing a single stage, or when you want more
control). Both follow the same process (design doc §2) and produce the
same files under `output/`; the guided path just sequences it and checks
in at the right moments so you don't have to remember the order yourself.

Either way, start the same way: open a terminal in this repo folder, run
`claude` to start a Claude Code session, make sure your required inputs
are in place (see above), and go.

### Guided: `/run-cycle`

Type `/run-cycle` in the Claude Code session. This is a project-specific
skill (`.claude/skills/run-cycle/SKILL.md`) that:

1. **Checks what's already been done.** If `output/` already has files in
   it from a prior session, it summarizes what it found and asks whether
   you want to resume from the next incomplete stage, redo a specific
   stage you name, or start over from Stage 1 — it won't guess, and won't
   silently overwrite anything.
2. **Checks your required inputs exist** (`job_posting.md`, `cv/`,
   `essay/`) before doing anything else, and tells you plainly if
   something's missing rather than making something up.
3. **Walks all 14 stages in order** (design doc §2), doing each one
   directly — itemizing and decomposing the JD/form, tagging your context,
   tailoring your CV, drafting variants, running the judge panel,
   aggregating results — stopping only at the checkpoints the design
   already calls for:
   - itemization review (Stages 1–2) — you check the itemised JD/form
     against the real posting, since an LLM asked to itemise can quietly
     compress or drop a line, and everything downstream scores against
     these files;
   - tagging approval (Stage 5) — you check the agent's read of your own
     material, a harder check than reviewing your own writing;
   - the interview handoff (Stage 6) — it writes a brief, you go have the
     actual conversation externally in a voice-mode app, then paste the
     result back;
   - agreeing draft axes before generating variants (Stage 10) — so
     exploration stays genuinely exploratory, not a rubber stamp;
   - confirming before it spends real API money running the judge panel
     (Stage 11);
   - the sniff check (Stage 13) — you read the top variants and the judge
     summary yourself and give direction for the next round.
4. Otherwise stays out of your way and just does the work — no unsolicited
   discussion of the pipeline's own design while a cycle is running;
   that's a separate conversation.

You can stop mid-cycle at any point (e.g. to go have the external
interview) and pick it back up later by invoking `/run-cycle` again — it
detects where things stand and asks how to proceed, per (1).

### Manual: stage by stage

Useful if you only want to redo one specific stage, or prefer to drive
each step yourself. Ask the agent for each stage in turn (see design doc
§2 for exactly what each needs as input and produces):

1. **JD & form decomposition** (Stages 1–2) — ask the agent to itemize
   `input/job_posting.md` into `output/jd_itemised.md`, then
   `output/form_itemised.md` for the application-form fields. **Check the
   itemised file against the actual posting yourself** — you'll already
   have it open, since you just pasted from it — and tell the agent
   directly what to fix if anything was dropped, paraphrased, or invented;
   this is a cheap but real checkpoint, since everything downstream scores
   against these files. Only once you're satisfied, have it decompose into
   `output/jd_components.json` / `output/form_questions.json`, and
   review/hand-edit that too.
2. **External reference ingestion** (Stage 4, optional) — the agent reads
   anything in `input/external_resources.md` / `input/external_refs/` and
   writes `output/external_references.md`.
3. **Context mapping** (Stage 5) — the agent tags fragments of everything
   in `input/essay/` (and any external references) against JD components,
   writes `output/tagged_context.json`/`.md`. Review it, especially
   anything flagged low-confidence — you're now checking an LLM's read of
   your own words, which is a harder check than reviewing your own
   writing.
4. **Reflective interview** (Stage 6) — ask the agent for an interview
   brief; it writes one to `output/interview_brief.md`. Paste that into a
   voice-mode app (Claude/Gemini/ChatGPT) and have the actual conversation
   there (Claude Code has no voice interface), then drop the result into
   `input/interview_transcripts/` for the agent to normalize into
   `output/interview_report.md`. Already had a relevant conversation on
   your own before starting this pipeline? Drop that transcript in the
   same folder — it doesn't need to have started from a brief this session
   generated. For a follow-up round, the agent checks what's already
   covered before drafting a new brief.
5. **Voice profiling** (Stage 8, optional) — needs `input/past_drafts/`
   (corrected text only, never raw dictated/transcribed originals —
   including interview transcripts, which get no exemption just because
   they're compelling, design doc §Stage 6); the agent distills
   `output/voice_profile.md` in one pass.
6. **CV tailoring** (Stage 9) — the agent produces `output/cv_tailored.md`
   + `output/cv_tailoring_notes.json`, tracing every claim back to a
   source fragment.
7. **Draft generation** (Stage 10) — in exploration mode, agree on a
   round's axes with the agent first (genuinely distinct angles for this
   application, not a generic grid), then each variant is drafted by its
   own forked subagent into `output/drafts/genN/vXX/`. In convergence
   mode, it's a single directed rewrite done straight in conversation.
8. **Judge panel** (Stage 11, exploration rounds only — the one scripted
   step, and the one that spends real API money):
   ```
   python scripts/run_judges.py --gen 1     # writes output/evals/gen1/
   ```
9. **Aggregation** (Stage 12) — the agent reads the eval files and pulls
   out recurring comments; the numeric rollup is deterministic:
   ```
   python scripts/aggregate.py --gen 1      # writes output/evals/gen1/summary.json + summary.md
   ```
   Read `summary.md` yourself.
10. **Sniff check + direction** (Stage 13, manual) — read the top 2–3
    variants and `summary.md`, then tell the agent your direction; it
    writes `output/rounds/gen1/direction.md`.
11. **Directed iteration** (Stage 14) — the agent reads that direction plus
    `summary.md` and `input/preferences.md` and writes
    `output/rounds/gen2/round_config.json`. Approve or adjust, then repeat
    from step 7 for gen 2.

See the design doc for the full pipeline (14 stages) and exactly what each
stage's input/output contract is.
