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
- `marking_guide.md` -> Stage 3 done
- `drafting_guide.md` -> Stage 4 done
- `external_references.md` -> Stage 6 done (or genuinely skipped, if no
  optional input existed)
- `tagged_context.json` -> Stage 7 done
- `interview_report.md` -> Stage 8 done for at least one round
- `voice_profile.md` -> Stage 10 done
- `cv_tailored.md` / `cv_tailoring_notes.json` -> Stage 11 done
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

## Step 2 -- Walk the stages in order, by phase

Per design doc §2's six phases. Do each stage's work directly (only Stage
13 is a separate script), then stop at the marked checkpoint or continue
automatically. Rationale for *why* a stage works this way lives in the
design doc / `history_and_rationale.md`, not here.

**Phase 1 -- Process the job post**

1. **JD decomposition** -- itemize `input/job_posting.md` ->
   `jd_itemised.md`. **STOP**: present it, ask Jeremy to verify against
   the live posting. Only after he confirms (or corrects), decompose ->
   `jd_components.json`. **STOP**: present it for review/hand-edit before
   continuing.
2. **Form decomposition** -- same pattern -> `form_itemised.md` (**STOP**,
   verify against the live form) -> `form_questions.json`.
3. **Marking guide co-creation** -- propose `output/marking_guide.md`
   from `jd_components.json` + `form_questions.json` (rubric anchors, id-
   verbatim instruction, `overall_score`->`overall_outcome` rule,
   comment-length cap). **STOP**: co-create this live with Jeremy, don't
   just present a finished file -- Stage 13 can't run without it.
4. **Drafting guide co-creation** -- propose `output/drafting_guide.md`
   (per-question content boundaries, whole-variant cohesion requirement,
   the overclaim consistency check). **STOP**: same live co-creation, not
   a rubber stamp -- Jeremy said he already has views on what each
   question should cover, so let him drive the actual boundaries.

**Phase 2 -- Import personal context**

5. **Essay capture** -- Jeremy-authored, already checked in Step 1.
   Nothing to do here except confirm `input/essay/` has what's needed.
6. **External reference ingestion** -- only if
   `input/external_resources.md` or `input/external_refs/` has content;
   skip silently if neither does (it's optional). -> `external_references.md`.
7. **Context mapping** -- tag everything in `input/essay/` +
   `external_references.md` against JD components/form questions ->
   `tagged_context.json`/`.md`. **STOP**: present it, flagging
   low-confidence fragments first -- don't let it get rubber-stamped.
8. **Reflective interview** -- check `input/interview_transcripts/` for
   anything not yet ingested; ingest what's there -> `interview_report.md`.
   Then ask: fresh interview round this cycle, or proceed with what's
   already ingested? If fresh: generate the brief, save it to
   `output/interview_brief.md`, tell Jeremy to have the conversation
   externally and drop the result in `input/interview_transcripts/`, and
   **pause the cycle here** -- this genuinely can't continue
   synchronously.
9. **Preferences** -- Jeremy-authored, read `input/preferences.md` if
   present; nothing to produce.
10. **Voice profiling** -- if `input/past_drafts/` has content, or
    `input/essay/` content is itself already proofread/polished for this
    application (ask if unclear, don't assume from folder alone) --
    otherwise skip. If `voice_profile.md` already exists, ask whether to
    refresh it or keep it (design doc §Stage 10).
11. **CV tailoring** -- tailor using everything in `input/cv/` + tagged
    context + JD components + preferences -> `cv_tailored.md` +
    `cv_tailoring_notes.json`. Present the result; not a hard stop, but
    flag anything that reads as a stretch against the `claims_checklist`
    (design doc, Stage 11).

**Phase 3 -- Draft variations**

12. **Draft generation** -- determine the round number and mode from
    `rounds/genN/round_config.json` (or default: gen 1, exploration, per
    design doc §4, if nothing exists). Every variant is written as one
    `drafts/genN/<variant_id>.md` file (all questions, each under a
    `## [q<question_id>] ...` heading -- see `data_schemas.md`), no
    per-variant folder, not one file per question. For **exploration
    mode**: propose a set of genuinely distinct axes for this round
    grounded in the actual material (not a generic grid) and **agree them
    with Jeremy before drafting anything** -- then fork one subagent per
    variant, each with the full context bundle (including
    `drafting_guide.md`) plus its one axis, writing its `<variant_id>.md`
    directly. For **convergence mode**: write the single directed draft
    straight in this conversation, incorporating the carried-forward
    direction. For **comparison mode**: assemble the variant set directly
    rather than drafting fresh -- copy a prior variant's `.md` unmodified
    for a carried-forward baseline, apply Jeremy's hand edits or an
    external tool's output for the others, and draft any genuinely new
    variant per its direction; write each variant's `<variant_id>.meta.json`
    with `production_method` and `derived_from` set accordingly
    (`data_schemas.md`).

**Phase 4 -- Naive HR screening**

13. **Judge panel** -- exploration rounds only. **Before running,
    check every variant + `cv_tailored.md` against the submission-ready
    checklist** (CLAUDE.md) -- no placeholders, no leftover internal
    notes, no near-duplicate answers within a variant. Fix anything that
    fails directly; don't send a known defect to the judge panel. Then:
    requires `marking_guide.md` (Stage 3) -- `run_judges.py` reads it for
    the rubric and fails loudly if it's missing. **Confirm with Jeremy
    before running** `python scripts/run_judges.py --gen N` -- it spends
    real API money against his real application content, same standing
    rule as any cost-incurring script in this repo.

**Phase 5 -- Aggregate & understand outcome**

14. **Aggregation** -- run `python scripts/aggregate.py --gen N` for the
    numeric rollup, then read the eval files directly and add the
    recurring-findings synthesis into `summary.md` yourself -- this half
    is agent-in-context, not scripted.
15. **Sniff check** -- **STOP**: present the top variants and
    `summary.md`, wait for Jeremy's read and direction, write
    `rounds/genN/direction.md` from what he says.

**Phase 6 -- Iterate**

16. **Directed iteration** -- read `direction.md` + `summary.md` +
    `preferences.md` -> `rounds/gen(N+1)/round_config.json`. Present it for
    approval, then loop back to step 12 (Phase 3) for the next generation
    if Jeremy wants another round.

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
