# job-app-eval

Agentic pipeline that drafts and evaluates a job application (CV +
written answers) against a job posting. You perform every stage
directly in this session, except Stage 13 (`scripts/run_judges.py`), a
separate scripted API call — isolated so the judge never sees the
drafting conversation.

- Design and rationale: @design/agentic_application_eval_design.md
- Decision history (rarely needed): @design/history_and_rationale.md
- Exact file/JSON shapes: `design/data_schemas.md` — check before
  hand-writing a schema that already has a defined shape.

## Running the pipeline

Use the `/run-cycle` skill (`.claude/skills/run-cycle/SKILL.md`) to
produce or advance an application — it sequences stages and checkpoints
and detects resume vs. restart. Manual-invoke only; don't replicate its
sequencing ad hoc when it isn't active.

## Privacy: what's public

This repo is public; `input/` and `output/` are not. Both are
gitignored — never commit them. They hold the application's actual
content and strategy (CV, essay, drafts, judge scores), not just
identifying details. Before any `git add` that touches either, confirm
`.gitignore` covers it — don't assume.

## Submission-ready checklist (run before Stage 13)

Cheap hygiene pass on `cv_tailored.md` and every drafted variant before
the judge panel runs — fix failures directly, don't hand a known defect
to the (expensive) panel:

- No placeholder tokens (`[TODO]`, `<...>`, unfilled contact info).
- No internal notes/meta-commentary inline in content — belongs in
  `cv_tailoring_notes.json` or conversation.
- No near-duplicate content between a variant's own answers.
- Word/character limits from `form_questions.json` respected.

## Stack notes

- Only `scripts/run_judges.py` (Stage 13) calls the Anthropic API.
  `scripts/aggregate.py` (Stage 14) is deterministic, no API key needed.
  Everything else is in-session agent reasoning.
- `scripts/deprecated/`: superseded pre-redesign scripts, kept for
  reference only — don't wire back in.
- `run_judges.py` requires `output/marking_guide.md` (Stage 3);
  Stage 12 requires `output/drafting_guide.md` (Stage 4) plus
  `voice_profile.md`. Both fail loudly if missing.
- A subagent needing scratch space for intermediate files (e.g. digesting
  many judge files into a synthesis) should use `output/`, already
  gitignored — not an OS temp path outside the repo.
