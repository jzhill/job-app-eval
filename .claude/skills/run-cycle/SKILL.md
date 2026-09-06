---
name: run-cycle
description: Execute the job-application pipeline end-to-end (design doc §2) -- check required inputs, detect existing output/ state and confirm resume vs. restart, then run each stage in order, stopping only at defined checkpoints or genuine ambiguity. For actually producing/advancing an application, not for discussing or redesigning the pipeline itself.
disable-model-invocation: true
---

# Run Cycle

This skill executes the pipeline described in `design/agentic_application_eval_design.md`
(§2) end-to-end, in this session, stage by stage. It is for actually
advancing a real application -- drafting, tagging, tailoring, generating,
judging -- not for discussing or changing the pipeline's design. If Jeremy
wants to talk through an architecture change, a new stage, or a script bug
while this is active, pause the cycle, have that conversation as normal,
and return to the cycle afterward rather than blending the two.

Read `design/agentic_application_eval_design.md` and
`design/data_schemas.md` now if they aren't already in context -- this
skill only covers *sequencing and checkpoints*; the stage contracts (exact
inputs/outputs, why a checkpoint exists) live there and shouldn't be
duplicated here.

## Step 0 -- Where does this cycle stand?

Check what already exists under `output/` (and `output/rounds/*/`) before
doing anything else:

- `jd_components.json`, `form_questions.json` -> Stages 1-2 done
- `external_references.md` -> Stage 4 done (or genuinely skipped, if no
  optional input existed)
- `tagged_context.json` -> Stage 5 done
- `interview_report.md` -> Stage 6 done for at least one round
- `voice_profile.md` -> Stage 8 done
- `cv_tailored.md` / `cv_tailoring_notes.json` -> Stage 9 done
- `drafts/genN/`, `evals/genN/`, `rounds/genN/direction.md`,
  `rounds/gen(N+1)/round_config.json` -> how far generation/judging/
  iteration has gotten, and for which round

**If nothing exists yet**, this is a fresh application -- skip to Step 1.

**If anything exists**, summarize what you found in plain terms ("JD and
form are decomposed, tagging is done, no CV tailoring yet") and ask
explicitly before proceeding:

- **Resume** -- pick up at the first stage that's missing or incomplete.
- **Redo a specific stage** -- Jeremy names it; re-run that stage and
  continue from there. Confirm before overwriting its existing output
  file(s).
- **Start over** -- re-run from Stage 1. Confirm before overwriting
  anything already there; nothing gets deleted, files are just
  regenerated in place as each stage reruns.

Don't guess which of these Jeremy wants -- this is exactly the kind of
ambiguity to surface, not resolve silently.

## Step 1 -- Required inputs present?

Before Stage 1, confirm the required inputs actually exist and have
content:

- `input/job_posting.md`
- `input/cv/` (at least one file)
- `input/essay/` (at least one file)

If any are missing or empty, stop and tell Jeremy exactly what's missing.
Don't fabricate placeholder content for any of these -- they're the whole
point of the human-authored/human-provided inputs (design doc §1).

## Step 2 -- Walk the stages in order

For each stage below, do the work directly (per design doc §1 --
everything except Stage 11 runs in this session, not as a separate
script), then either stop at the marked checkpoint or continue
automatically.

1. **JD decomposition** -- itemize `input/job_posting.md` ->
   `jd_itemised.md`. **STOP**: present it, ask Jeremy to verify against
   the live posting. Only after he confirms (or corrects), decompose ->
   `jd_components.json`. **STOP**: present it for review/hand-edit before
   continuing.
2. **Form decomposition** -- same pattern -> `form_itemised.md` (**STOP**,
   verify against the live form) -> `form_questions.json`.
3. **Essay capture** -- Jeremy-authored, already checked in Step 1.
   Nothing to do here except confirm `input/essay/` has what's needed.
4. **External reference ingestion** -- only if
   `input/external_resources.md` or `input/external_refs/` has content;
   skip silently if neither does (it's optional). -> `external_references.md`.
5. **Context mapping** -- tag everything in `input/essay/` +
   `external_references.md` against JD components/form questions ->
   `tagged_context.json`/`.md`. **STOP**: present it, flagging
   low-confidence fragments first -- this is the harder checkpoint (design
   doc §Stage 5), don't let it get rubber-stamped.
6. **Reflective interview** -- check `input/interview_transcripts/` for
   anything not yet ingested; ingest what's there -> `interview_report.md`.
   Then ask: fresh interview round this cycle, or proceed with what's
   already ingested? If fresh: generate the brief, save it to
   `output/interview_brief.md`, tell Jeremy to have the conversation
   externally and drop the result in `input/interview_transcripts/`, and
   **pause the cycle here** -- this genuinely can't continue
   synchronously.
7. **Preferences** -- Jeremy-authored, read `input/preferences.md` if
   present; nothing to produce.
8. **Voice profiling** -- only if `input/past_drafts/` has content. If
   `voice_profile.md` already exists, ask whether to refresh it or keep it
   (design doc §8 -- this is meant to be a stable, one-time distillation,
   not something to casually regenerate).
9. **CV tailoring** -- tailor using everything in `input/cv/` + tagged
   context + JD components + preferences -> `cv_tailored.md` +
   `cv_tailoring_notes.json`. Present the result; not a hard stop, but
   flag anything that reads as a stretch (design doc §9 -- this is a first
   pass, Stage 11 is the real backstop, but don't let that be an excuse to
   wave through something questionable here).
10. **Draft generation** -- determine the round number and mode from
    `rounds/genN/round_config.json` (or default: gen 1, exploration, per
    design doc §4, if nothing exists). For **exploration mode**: propose a
    set of genuinely distinct axes for this round grounded in the actual
    material (not a generic grid) and **agree them with Jeremy before
    drafting anything** (design doc §Stage 10) -- then fork one subagent
    per variant, each with the full context bundle plus its one axis,
    writing `drafts/genN/vXX/` directly. For **convergence mode**: write
    the single directed draft straight in this conversation, incorporating
    the carried-forward direction.
11. **Judge panel** -- exploration rounds only. **Confirm with Jeremy
    before running** `python scripts/run_judges.py --gen N` -- it spends
    real API money against his real application content, same standing
    rule as any cost-incurring script in this repo.
12. **Aggregation** -- run `python scripts/aggregate.py --gen N` for the
    numeric rollup, then read the eval files directly and add the
    recurring-findings synthesis into `summary.md` yourself (design doc
    §12 -- this half is agent-in-context, not scripted).
13. **Sniff check** -- **STOP**: present the top variants and
    `summary.md`, wait for Jeremy's read and direction, write
    `rounds/genN/direction.md` from what he says.
14. **Directed iteration** -- read `direction.md` + `summary.md` +
    `preferences.md` -> `rounds/gen(N+1)/round_config.json`. Present it for
    approval, then loop back to step 10 for the next generation if Jeremy
    wants another round.

## While this is active

- Ask when genuinely blocked or ambiguous (a JD line that itemizes two
  reasonable ways, a fragment whose component mapping is a toss-up) --
  don't silently pick one and move on. Otherwise stay on task: this mode
  is for producing the application, not for re-litigating the pipeline's
  design.
- Never overwrite an existing output file as part of "resume" without
  having confirmed that's what Jeremy wants (Step 0).
- Confirm before any script run that spends real API money
  (`run_judges.py`) -- standing rule, not just a run-cycle one.
