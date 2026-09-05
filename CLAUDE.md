# job-app-eval

A small Python pipeline that automates a manual workflow Jeremy already ran
by hand in a browser Claude session: drafting and evaluating a "Why
Anthropic" job application essay against a job description, using a
multi-judge LLM panel instead of gut-feel.

Full design: @design/agentic_application_eval_design.md

## Repo layout and what's public

This repo is intended to be **public** (it's part of the application itself
— showing the work). That has one consequence baked into `.gitignore`:

- `input/` is **gitignored, never committed.** It holds everything
  human-provided: `job_posting.md`, `current_cv.*`, `essay_response.md`,
  and optionally `external_resources.md`/`external_refs/`/`past_drafts/`.
  Treat everything under `input/` as private even though the rest of the
  repo is public — see README.md for the exact required/optional files.
- Everything the pipeline *generates* from that input (`jd_components.json`,
  `form_questions.json`, `tagged_context.json`, `preferences.md`,
  `voice_profile.md`, `drafts/`, `evals/`) is intended to be committed and
  public — that's the actual point of the repo. If a generated file ends
  up containing something overly identifying, flag it before committing
  rather than assuming the split in `.gitignore` alone handles it.

## Core principle (from the design doc)

Everything is scored against the job description, not a generic rubric.
`jd_components.json` is the spine every downstream score ties back to.

## Working with Jeremy

- New to Claude Code (comfortable with GUI IDEs, has CS fundamentals) —
  explain CLI-specific mechanics briefly when they matter, don't assume
  prior exposure to this tool specifically.
- Stays in the loop by design at three points: approving the context
  mapping (Stage 5), participating directly in the reflective interview
  (Stage 6), and doing the manual "sniff test" + supplying direction after
  each judge-panel round (Stage 13). Don't script past these checkpoints
  even if it would be easy to automate them.
- Prefers direct, specific, sometimes blunt feedback over generic
  encouragement. Wants AI to do heavy lifting on structure/condensation/
  polish, but substantive claims about his experience must originate from
  him — don't invent or embellish biographical content on his behalf.
- Wants exactly what's asked for, nothing more — no unsolicited features,
  refactors, or abstractions in code; no unsolicited rewrites in prose.
  Always still flag a genuine gap or better approach, then wait.
- A real factual correction already happened once (see design doc §5):
  earlier essay drafts overclaimed formal AI model validation/calibration
  in the Kiribati work. The accurate framing — vendor collaboration with
  Delft/Fuji + implementation/capability evaluation, not calibration — is
  a hard constraint, not a style preference. Don't let generation drift
  back toward the overclaim.

## Stack notes

- Use the Anthropic API directly (not Claude Code's own agentic loop) for
  Stage 10 draft generation and Stage 11 judging — each call should be a
  clean, scriptable, loggable unit, per the design doc.
- Pipeline stages are separate scripts under `scripts/`, each independently
  rerunnable (e.g. rerun judging alone after tweaking the panel, without
  regenerating drafts).
- Exact JSON shapes for generated files live in `design/data_schemas.md`,
  not in the main design doc — check there before hand-writing a schema
  that already has a defined shape.
