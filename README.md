# job-app-eval

A pipeline that drafts and evaluates a job application (CV + written
answers) against a specific job posting, using a multi-judge LLM panel,
to maximize the chance of being screened in. Full design:
[`design/agentic_application_eval_design.md`](design/agentic_application_eval_design.md).

**Most of this pipeline is not a script you run — it's a conversation
you have with Claude Code in this folder.** Only the judge-panel step
(Stage 13) is a separate scripted call to the Anthropic API, because
that's the one stage whose whole value depends on the judge not having
seen the conversation that produced the draft it's evaluating. Every
other stage is something you ask the agent to do directly, with full
context and room to ask you a clarifying question instead of quietly
guessing.

## Background

This started as a manual pilot for one specific application (Anthropic's
Partner Manager, Global Health role): drafting an essay by hand across
several revisions, then running each version through a naive LLM acting
as an HR screener. A clear, consistent pattern of findings emerged —
evidence the naive-screener approach surfaces real signal, not noise —
which is why this repo formalizes that manual workflow into a repeatable
pipeline instead of relying on nine ad hoc runs read by hand. There's
also a second, more pointed reason to build it well: a tool that
evaluates and improves an application for an AI safety company, built
using careful, skeptical evaluation methodology, is itself a small
demonstration of the kind of judgment the role is looking for.

Only code and documentation are public here — `input/` and `output/` are
both gitignored, full stop. Draft text, judge scores, and the tailored
CV are the application's actual substance and strategy, not a
repackaging of public information, so none of it belongs in a public
repo.

## Setup

1. `python -m venv .venv` then `.venv/Scripts/activate` (Windows) or
   `source .venv/bin/activate` (Mac/Linux), then
   `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and fill in your key from
   console.anthropic.com: `ANTHROPIC_API_KEY=sk-ant-...`. Never commit
   it. Only `scripts/run_judges.py` (Stage 13) actually needs it at
   runtime — everything else in the active pipeline runs as the Claude
   Code agent's own reasoning, not a separate API call.

## Input files (place in `input/`)

| File/folder | Required? | What it is |
|---|---|---|
| `job_posting.md` | Required | Copy-paste the raw text of the job posting, straight from the browser. If the application form's fields are on the same page (common on Greenhouse and similar ATS platforms), paste those too. |
| `cv/` | Required | One or more CV versions, any format (`.docx`/`.pdf`/`.md`)/filename — the agent reconciles across them when tailoring. |
| `essay/` | Required | Free-written material, one or more files, any filename — your own words on why this role, relevant experience, motivation. No structure required; the pipeline maps this onto the posting's requirements for you. |
| `preferences.md` | Optional | How you want the pipeline to weight things — priorities, hard constraints that must never be reverted. |
| `external_resources.md`, `external_refs/` | Optional | URLs (one per line, with an optional note) or files with relevant background on the employer. |
| `interview_transcripts/` | Optional | Transcripts/notes from a live interview conversation — one you already had, or one prompted by a brief the agent generates. |
| `past_drafts/` | Optional | Prior application drafts, **corrected/proofread text only** — used to build a voice profile, along with `input/essay/` content too if that's already polished for this application rather than rough freewriting. Proofread status is what matters, not which folder a file sits in — say so if it's ambiguous. |

Everything the pipeline generates lands in `output/`, gitignored the
same way — see the design doc §3 for the full layout and
[`data_schemas.md`](design/data_schemas.md) for exact file shapes.

## Usage

Open a terminal in this repo folder, run `claude` to start a Claude Code
session, make sure your required inputs are in place, and go.

**Guided (recommended):** type `/run-cycle`. This project skill
(`.claude/skills/run-cycle/SKILL.md`) checks what's already been done,
confirms your required inputs exist, and walks the whole pipeline in
order — stopping only at the checkpoints the design calls for (itemization
review, marking/drafting guide co-creation, context-mapping approval, the
interview handoff, agreeing draft axes, confirming before it spends real
API money on the judge panel, and the sniff check). You can stop mid-cycle
(e.g. to go have the external interview) and pick it back up later; it
detects where things stand and asks how to proceed.

**Manual (stage by stage):** useful if you only want to redo one stage,
or prefer to drive each step yourself — just ask the agent for a specific
stage by name. See the design doc §2 for exactly what each stage needs as
input and produces, and `data_schemas.md` for exact file shapes. The two
scripted steps, run directly when you reach them:

```
python scripts/run_judges.py --gen 1     # Stage 13 — writes output/evals/gen1/
python scripts/aggregate.py --gen 1      # Stage 14 — writes output/evals/gen1/summary.json + summary.md
```
