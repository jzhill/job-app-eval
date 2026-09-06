# job-app-eval

A small Python pipeline that automates a manual workflow Jeremy already ran
by hand in a browser Claude session: drafting and evaluating a "Why
Anthropic" job application essay against a job description, using a
multi-judge LLM panel instead of gut-feel.

Full design: @design/agentic_application_eval_design.md

## Repo layout and what's public

This repo is public — but only the **code and documentation** (the
methodology, the pipeline, the design rationale), not any actual
application content. That's a deliberate, important distinction: an
earlier version of this project committed generated files on the theory
that they just reproduced public posting text, which missed that draft
essay text, judge scores/critiques, and the tailored CV are the
application's actual substance and strategy, not public information.

- `input/` is **gitignored, never committed.** Everything human-provided:
  `job_posting.md`, `current_cv.*`, `essay_response.md`, and optionally
  `external_resources.md`/`external_refs/`/`past_drafts/` — see README.md
  for the exact required/optional files.
- **Everything the pipeline generates from a real run is also gitignored**
  — `jd_components.json`, `form_questions.json`, `tagged_context.json`,
  `preferences.md`, `voice_profile.md`, `drafts/`, `evals/`, `rounds/`,
  all of it. None of it gets committed. If you're ever about to `git add`
  one of these, stop — check `.gitignore` covers it, don't assume.

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
- A real overclaim already made it through several drafting rounds once
  during the original pilot before being caught (see README.md
  "Background" for the actual story — deliberately not repeated here or
  in the design doc, since neither should hardcode one application's
  specific content). This is why `overclaim_risk` is a permanent,
  hard-constraint judge score, not a style preference — don't let
  generation drift back toward overstating ownership of collaborative
  work.

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
