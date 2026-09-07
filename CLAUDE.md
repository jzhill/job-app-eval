# job-app-eval

A pipeline, run as a live Claude Code session, that drafts and evaluates
a job application (CV + written answers) against a specific job posting,
to maximize the chance of being screened in. Only the judge panel (Stage
13) is a separate script calling the Anthropic API — everything else is
done by the agent operating directly in this repo. Full design, including
*why* it's built this way: @design/agentic_application_eval_design.md.
Decision history and extended rationale not needed day-to-day:
@design/history_and_rationale.md.

To actually produce/advance an application end-to-end (not to discuss or
redesign the pipeline), invoke the `/run-cycle` skill
(`.claude/skills/run-cycle/SKILL.md`) — it walks the stages in order,
checkpoint by checkpoint, and checks in before resuming vs. restarting.
It's manual-invoke only; don't replicate its sequencing logic ad hoc when
it isn't active.

## Repo layout and what's public

This repo is public — but only the **code and documentation**, not any
actual application content. `input/` and `output/` are **both gitignored,
never committed**: `input/` is what Jeremy provides (`job_posting.md`,
`cv/`, `essay/`, and other optional folders — see README.md for the
exact list); `output/` is everything the pipeline generates from it
(decomposed JD/form, tagged context, drafts, judge evals, everything).
Draft text, judge scores, and the tailored CV are the application's
actual substance and strategy, not public information. If you're ever
about to `git add` a file under either directory, stop — check
`.gitignore` covers it, don't assume.

## Working with Jeremy

- New to Claude Code (comfortable with GUI IDEs, has CS fundamentals) —
  explain CLI-specific mechanics briefly when they matter, don't assume
  prior exposure to this tool specifically.
- Stays in the loop by design at three points: approving context mapping
  (Stage 7), participating directly in the reflective interview (Stage
  8), and the sniff test + direction after each judge-panel round (Stage
  15). These are moments within the ongoing conversation to stop and
  check in, not separate steps to skip past.
- Prefers direct, specific, sometimes blunt feedback over generic
  encouragement. Wants AI to do heavy lifting on structure/condensation/
  polish, but substantive claims about his experience must originate from
  him — don't invent or embellish biographical content on his behalf.
- Wants exactly what's asked for, nothing more — no unsolicited features,
  refactors, or abstractions in code; no unsolicited rewrites in prose.
  Always still flag a genuine gap or better approach, then wait.
- The overclaim guard (design doc §5, Stages 4/11) is a permanent,
  load-bearing rule, not a style preference — don't let generation drift
  back toward overstating ownership of collaborative work.

## Submission-ready checklist

Run this before Stage 13 (design doc, Stage 13 precondition) — a cheap,
non-naive hygiene pass over `cv_tailored.md` and every drafted variant,
not a judgment call the panel needs to be naive to make:

- No placeholder tokens (unfilled contact info, `[TODO]`, `<...>`, etc.)
  anywhere in the actual file content.
- No leftover internal notes or meta-commentary in the content itself —
  editorial asides belong in `cv_tailoring_notes.json` or conversation,
  never inline in `cv_tailored.md` or a draft answer.
- No near-duplicate content between a variant's own answers — each
  question should say something distinct from the others in that variant.
- Word/character limits from `form_questions.json` respected.

Fix directly if something fails; don't hand a known defect to the
(expensive) judge panel and let it get flagged repeatedly instead.

## Stack notes

- Only Stage 13 (`scripts/run_judges.py`) calls the Anthropic API. Every
  other stage is performed by the Claude Code agent directly in this
  session — see design doc §1 for why.
- `scripts/` holds only `_common.py`, `run_judges.py`, and `aggregate.py`
  (Stage 14's deterministic numeric rollup — no API key needed).
  `scripts/deprecated/` holds superseded per-stage scripts from before
  the in-context redesign — kept for reference, not run as part of the
  active pipeline; don't wire them back in.
- Exact JSON/file shapes live in `design/data_schemas.md`, not the main
  design doc — check there before hand-writing a schema that already has
  a defined shape.
- `run_judges.py` requires `output/marking_guide.md` (Stage 3) to exist
  and fails loudly if it doesn't. Stage 12 similarly requires
  `output/drafting_guide.md` (Stage 4) as a fixed input alongside
  `voice_profile.md`.
