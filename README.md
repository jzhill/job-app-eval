# job-app-eval

Meta-job application, with agentic evaluation. A pipeline that drafts and
evaluates job-application text (essay questions + tailored CV) against a
specific job posting, using a multi-judge LLM panel. Full design:
[`design/agentic_application_eval_design.md`](design/agentic_application_eval_design.md).

## Setup

1. `python -m venv .venv` then `.venv/Scripts/activate` (Windows) or
   `source .venv/bin/activate` (Mac/Linux), then
   `pip install -r requirements.txt`.
2. Set `ANTHROPIC_API_KEY` in your environment before running any script —
   generation and judging call the Anthropic API directly.
3. `input/` is gitignored — nothing you put there is committed. Everything
   the pipeline generates from it (itemised JD/form, decomposed components,
   drafts, evals) is committed and public.

## Required inputs (place in `input/`)

| File | What it is |
|---|---|
| `job_posting.md` | Copy-paste the **raw text of the job posting**, straight from the browser. If the application form's fields are on the same page (common on Greenhouse and similar ATS platforms), paste those too — one file covers both. |
| `current_cv.docx` / `.pdf` / `.md` | Your current CV, whichever format you already have. |
| `essay_response.md` | Write freely — your own words on why this role, relevant experience, motivation. No structure required, no need to address specific requirements one by one; just write toward the posting loosely. The pipeline maps this onto the posting's actual requirements for you. |

## Optional inputs

| File/folder | What it is |
|---|---|
| `external_resources.md` | A list of URLs (articles, org pages, reports) you find relevant background, one per line, with an optional note on why. |
| `external_refs/` | Any files (PDFs etc.) that serve the same purpose. |
| `past_drafts/` | Prior application drafts, if you have any — used to build a voice profile of your writing style. |

## How the JD/form intake checkpoint works

`scripts/decompose_jd.py` and `scripts/decompose_form.py` break
`job_posting.md` into a numbered, itemised list (`jd_itemised.md` /
`form_itemised.md`) before decomposing it further. **After running these,
check the itemised file against the actual posting yourself** — you'll
already have it open, since you just pasted from it. Confirm nothing was
dropped or altered, or fix the specific item. This is a cheap but real
checkpoint: an LLM asked to itemise a posting can quietly compress or drop
a line, and everything downstream scores against this file.

## Running the pipeline

Once the required inputs are in place:

```
python scripts/decompose_jd.py                  # writes jd_itemised.md -- review it
python scripts/decompose_jd.py --decompose       # writes jd_components.json -- review/edit it

python scripts/decompose_form.py                 # writes form_itemised.md -- review it
python scripts/decompose_form.py --decompose      # writes form_questions.json

python scripts/ingest_references.py               # optional, writes external_references.md

python scripts/tag_context.py                     # writes tagged_context.json/.md -- review it,
                                                    # especially anything flagged low-confidence

python scripts/interview.py                        # writes interview_brief.md -- paste into a
                                                    # voice-mode app (Claude/Gemini/ChatGPT),
                                                    # have the conversation, save what it gives you
python scripts/interview.py --ingest <path>        # writes interview_report.md from that output

python scripts/build_voice_profile.py              # optional, needs input/past_drafts/*.md
python scripts/tailor_cv.py                        # writes cv_tailored.md + cv_tailoring_notes.json

python scripts/generate_drafts.py --gen 1          # writes drafts/gen1/vNN/
python scripts/run_judges.py --gen 1               # writes evals/gen1/ (skipped in convergence rounds)
python scripts/aggregate.py --gen 1                # writes evals/gen1/summary.md -- read this yourself

# write rounds/gen1/direction.md yourself (see design doc §Stage 13), then:
python scripts/plan_next_gen.py --gen 1            # writes rounds/gen2/round_config.json
python scripts/generate_drafts.py --gen 2          # next round, repeat
```

See the design doc for the full pipeline (14 stages) and what each script
produces.
