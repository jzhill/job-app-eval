# job-app-eval

A small Python pipeline that automates a manual workflow Jeremy already ran
by hand in a browser Claude session: drafting and evaluating a "Why
Anthropic" job application essay against a job description, using a
multi-judge LLM panel instead of gut-feel.

Full design: @design/agentic_application_eval_design.md

## Repo layout and what's public

This repo is intended to be **public** (it's part of the application itself
— showing the work). That has one consequence baked into `.gitignore`:

- `input/` is **gitignored, never committed.** It holds raw personal source
  material — CV, essay drafts, the handover doc — which contains Jeremy's
  name, comp band, current location, and visa status. Treat anything in
  `input/` as private even though the rest of the repo is public.
- Everything the pipeline *generates* from that input (`context.md`,
  `preferences.md`, `voice_profile.md`, `jd_components.json`, `variants/`,
  `evals/`) is intended to be committed and public — that's the actual
  point of the repo. If a generated file ends up containing something
  overly identifying (e.g. the comp figure), flag it before committing
  rather than assuming the split in `.gitignore` alone handles it.

## Core principle (from the design doc)

Everything is scored against the job description, not a generic rubric.
`jd_components.json` is the spine every downstream score ties back to.

## Working with Jeremy

- New to Claude Code (comfortable with GUI IDEs, has CS fundamentals) —
  explain CLI-specific mechanics briefly when they matter, don't assume
  prior exposure to this tool specifically.
- Stays in the loop by design at two points: after context-gathering
  (approves `context.md`) and after each judge-panel round (does a manual
  "sniff test" before the next generation runs). Don't script past these
  checkpoints even if it would be easy to automate them.
- Prefers direct, specific, sometimes blunt feedback over generic
  encouragement (see handover doc §5). Wants AI to do heavy lifting on
  structure/condensation/polish, but substantive claims about his
  experience must originate from him — don't invent or embellish
  biographical content on his behalf.
- A real factual correction already happened once (see design doc §5 and
  handover doc §3): earlier essay drafts overclaimed formal AI model
  validation/calibration in the Kiribati work. The accurate framing —
  vendor collaboration with Delft/Fuji + implementation/capability
  evaluation, not calibration — is a hard constraint, not a style
  preference. Don't let generation drift back toward the overclaim.

## Stack notes

- Use the Anthropic API directly (not Claude Code's own agentic loop) for
  Stage 4 variant generation — each call should be a clean, scriptable,
  loggable unit, per the design doc.
- Pipeline stages are separate scripts under `scripts/`, each independently
  rerunnable (e.g. rerun judging alone after tweaking the panel, without
  regenerating variants).
