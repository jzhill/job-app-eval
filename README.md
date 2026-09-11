# job-app-eval

A pipeline that ingests your rough draft, optimises, and evaluates a job application (CV + written
answers) against a specific job posting, using a multi-judge LLM panel,
to maximize the chance of being screened in.

Full design:
[`design/agentic_application_eval_design.md`](design/agentic_application_eval_design.md).

## Usage

1. Drop your content in input/
2. Save your anthropic API KEY to .env
3. Run claude in the folder
4. /run-cycle to initiate
5. Drafts and evals appear in output/

## Background

The idea for this pipeline came while composing an application for a job posting at Anthropic - Partner Manager, Global Health. Aim is to automate what one might otherwise do in a chat window, learn a bit, and submit a reasonable application.

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

All .gitignored

|File/folder|Required?|What it is|
|-|-|-|
|`job_posting.md`|Required|Paste raw text from the job posting.|
|`cv/`|Required|One or more CV versions, any format (`.docx`/`.pdf`/`.md`)|
|`essay/`|Required|Your own draft application, or essay responding to the application.|
|`preferences.md`|Optional|How you want the pipeline to weight input context|
|`external_resources.md`, `external_refs/`|Optional|URLs (one per line, with an optional note) or files|
|`interview_transcripts/`|Optional|Transcripts/notes from a live agent interview, in which you might explore your motivation and ambition for this role|
|`past_drafts/`|Optional|Prior application drafts, to build a voice profile|

## Output files (appear in `output/`)

Also .gitignored

Everything the pipeline generates lands in `output/`, see the design doc §3 for the full layout and
[`data_schemas.md`](design/data_schemas.md) for exact file shapes.

