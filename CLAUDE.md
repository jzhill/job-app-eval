# job-app-eval

A pipeline, run as a live Claude Code session, that automates a manual
workflow Jeremy already ran by hand in a browser Claude session: drafting
and evaluating a "Why Anthropic" job application essay against a job
description, using a multi-judge LLM panel instead of gut-feel. Only the
judge panel itself is a separate script calling the Anthropic API —
everything else is done by the agent operating directly in this repo (see
"Core principle" below).

Full design: @design/agentic_application_eval_design.md

To actually produce/advance an application end-to-end (not to discuss or
redesign the pipeline), invoke the `/run-cycle` skill
(`.claude/skills/run-cycle/SKILL.md`) — it walks the stages in order,
checkpoint by checkpoint, and checks in before resuming vs. restarting.
It's manual-invoke only; don't replicate its sequencing logic ad hoc when
it isn't active.

## Repo layout and what's public

This repo is public — but only the **code and documentation** (the
methodology, the pipeline, the design rationale), not any actual
application content. That's a deliberate, important distinction: an
earlier version of this project committed generated files on the theory
that they just reproduced public posting text, which missed that draft
essay text, judge scores/critiques, and the tailored CV are the
application's actual substance and strategy, not public information.

- `input/` and `output/` are **both gitignored, never committed** — the
  whole rule fits in one line: `input/` is what Jeremy provides
  (`job_posting.md`, `cv/`, `essay/`, optionally `preferences.md`/
  `external_resources.md`/`external_refs/`/`interview_transcripts/`/
  `past_drafts/`); `output/` is everything the pipeline generates from it
  (decomposed JD/form, tagged context, drafts, judge evals, everything).
  Several of the input folders (`cv/`, `essay/`, `interview_transcripts/`)
  take any number of files with any filename — the agent reads and
  reconciles everything dropped in, rather than expecting one canonical
  file. See README.md for the exact required/optional input files. If
  you're ever about to `git add` a file under either directory, stop —
  check `.gitignore` covers it, don't assume.

## Core principle (from the design doc)

Everything is scored against the job description, not a generic rubric.
`jd_components.json` is the spine every downstream score ties back to.

A second principle governs *how* each stage runs: naivety is scarce, and
only Stage 11 (the judge panel) actually needs it — that's the only stage
whose value depends on the executor not having shared context with
whatever produced the material it's judging. Every other stage is
performed directly by the Claude Code agent in this session, not a
separate script. See design doc §1.

## Working with Jeremy

- New to Claude Code (comfortable with GUI IDEs, has CS fundamentals) —
  explain CLI-specific mechanics briefly when they matter, don't assume
  prior exposure to this tool specifically.
- Stays in the loop by design at three points: approving the context
  mapping (Stage 5), participating directly in the reflective interview
  (Stage 6), and doing the manual "sniff test" + supplying direction after
  each judge-panel round (Stage 13). Now that most stages run as direct
  conversation rather than script-then-review, these are moments within
  that conversation to stop and check in, not separate steps to skip past
  even though skipping would be easy.
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
  work. CV tailoring (Stage 9) runs in-context like most other stages now,
  but that doesn't weaken this guard: self-review already failed once in
  the original near-miss, which is exactly why Stage 11's naive, isolated
  judge panel — not the tailoring step itself — is the backstop that has
  to actually catch it.

## Stack notes

- Only Stage 11 (judging, `scripts/run_judges.py`) calls the Anthropic API
  directly. Draft generation (Stage 10) moved in-context — variant
  independence is preserved by forking one subagent per variant, not by
  routing generation through a separate API call. Every stage besides 11
  is performed by the Claude Code agent operating in this session; see
  design doc §1 for why the split lands exactly there.
- `scripts/` holds only `_common.py`, `run_judges.py`, and
  `aggregate.py` (Stage 12's deterministic numeric rollup — no API key
  needed). There's no script for the other stages and none is needed:
  the agent produces the same output files directly, per design doc §2.
  `scripts/deprecated/` holds the superseded per-stage scripts from
  before this redesign — kept for reference, not run as part of the
  active pipeline. Don't wire them back in; if the design ever reverts
  to script-per-stage, move them back rather than rewriting from scratch.
- Exact JSON shapes for generated files live in `design/data_schemas.md`,
  not in the main design doc — check there before hand-writing a schema
  that already has a defined shape. Those shapes are the contract
  regardless of whether a script or the agent produced the file.
