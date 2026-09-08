# Backlog — process/design issues raised during live runs

Not a design doc, not prescriptive — a running log of issues, confusions,
or possible improvements noticed while actually running the pipeline
end-to-end. Revisit deliberately (scope, decide, then fold into the
design doc or data schemas if adopted) rather than acting on these
mid-cycle. Newest entries at the top.

---

## 2026-09-07 — Reflection: would a finer judge scale (e.g. /20) have distinguished q_why_anthropic?

**Raised by Jeremy**, after the gen4 comparison round scored all four
`q_why_anthropic` variants identically (mean 4.67/5, one judge giving 4,
two giving 5, every time) despite the `r4v1` interview-driven rewrite
drawing a qualitatively distinct comment from at least one judge
("distinctive clinician's framing... slight drift toward foundational
model work"). **A note for reflection, not a task** — Jeremy was explicit
this doesn't need action.

Worth being skeptical that widening the scale alone would surface real
distinction: the judge already registered something different in the
free-text comment without it moving the 1-5 score, which cuts against
"the scale was just too coarse" as the explanation. Asking an LLM judge
(like a human rater) for more precision than it actually has tends to
manufacture noise that looks like signal rather than reveal hidden signal
-- and gen1's own finding (6 of 7 variants statistically indistinguishable)
is consistent with these being genuinely close, not under-resolved.

**If this gets picked up later**, comparative/pairwise judging ("which of
these two is stronger, and why") is a more likely fix than a wider
absolute scale -- better-evidenced (human-rater and LLM-judge literature
both) for discriminating between close variants than adding resolution to
an independent per-variant score.

---

## 2026-09-07 — Recognisable AI tone/style persists despite voice_profile.md; humanizing approach deferred

**Raised by Jeremy**, on first read of gen3 v01: even with `voice_profile.md`
(Stage 10) informing drafting, the output still reads with recognisable AI
tone/style, not genuinely his voice. Floated idea: build a dedicated
"humanizing" skill/reference from curated real-world (non-AI) writing
examples, distilled into patterns to apply during drafting — a bigger
investment than `voice_profile.md`'s current approach.

**Decision: deferred, not building now.** Two options were on the table
(lightweight guidance added directly to `voice_profile.md`/
`drafting_guide.md` naming specific AI-tone tics, vs. the dedicated skill)
— Jeremy chose to defer both and prioritize getting `q_why_anthropic`
right first via a dedicated interview (see `rounds/gen3/direction.md`),
not spend a session on tone right now.

**Not yet decided — options to consider when this gets picked up:**
- Lightweight first: name the actual recurring tics (em-dash pileups,
  triadic phrasing, "it's not just X, it's Y" constructions, etc.)
  explicitly in `voice_profile.md`/`drafting_guide.md` and see if that
  alone is enough.
- Dedicated skill: gather curated examples (AI-tone vs. genuinely human
  counterexamples), distill into a reusable reference, apply as an
  explicit drafting pass — worth it only if the lightweight fix turns out
  insufficient.
- Worth checking against real output before either: is this actually
  still present in gen4 after the q_why_anthropic rewrite and repetition
  fix, or does some of it resolve as a side effect of those changes?

---

## 2026-09-07 — Subagent tried to write a scratch file outside the working directory

**Raised by Jeremy**, mid-Stage-14: the `gen2-synthesis` fork (reading all
21 gen2 judge files to write the qualitative synthesis) attempted to
`Read` a self-created scratch file at `\tmp\gen2_digest.txt` — outside
the repo working directory, which triggered Claude Code's own
outside-working-directory permission guardrail. Not a job-app-eval design
issue (no pipeline stage asks for this), but a genuine process wrinkle:
subagents doing large-file digestion work apparently sometimes create
their own intermediate scratch files, and default to an OS-level temp
path rather than something repo-local.

**Not yet decided:**
- Whether this needs an explicit instruction anywhere (a fork/subagent
  briefing convention, or a note in `CLAUDE.md`) telling agents that if
  they need scratch space, it should live under `output/` (already
  gitignored) rather than an external temp directory — or whether this
  is rare/cheap enough to just deny the permission prompt each time it
  comes up and let the agent recover by working in-context instead.
- No repo changes made — flagged for awareness only.

---

## 2026-09-07 — Judge/draft prompt complexity flagged again; single-document draft format proposed (not yet scoped)

**Raised by Jeremy**, immediately after gen2's judge panel run needed two
rounds of script fixes to complete (see `run_judges.py`/`_common.py`
changes this session): `max_tokens` raised 16k→32k after judges
repeatedly returned syntactically valid JSON that silently dropped all
`preferred_qualifications`/`core_responsibilities` scores partway through
a 26-item enumeration (only `required_qualifications`'s 8 items present,
identical missing-key list across multiple judges/models/variants — not
random flakiness), then a further fix to use the Messages API's streaming
mode once the larger `max_tokens` pushed calls past the SDK's non-
streaming request-duration limit. Both fixes were reactive patches to
symptoms already flagged in the 2026-09-06 retrospective's #2/#3 findings
("the current judge output schema asks for more free-form prose, across
more fields, than either the budget or the failure rate can comfortably
support") — today's schema is if anything heavier than the one that
prompted that finding (added `section_assessments` and the fuller
`input/job_posting.md` text on top of the existing 26-component/
4-question/CV enumeration), so the underlying complexity concern was
never actually resolved, just worked around again.

**Separately, a structural idea for draft generation, since resolved:**
Jeremy noticed draft variants sometimes show strong content overlap, and
floated whether Stage 12 should produce **one cohesive `.md` document per
variant** (all four answers as a single continuous composition) instead
of four separately generated files, on the theory that a model drafting
one unified document naturally reasons about repetition/flow across the
whole thing, rather than needing `drafting_guide.md`'s cohesion
instruction to compensate for four independently-generated pieces after
the fact.

**Resolved 2026-09-07 (part of the round-4 comparison/edited-variant
feature work — see `rounds/gen3/direction.md` and `rounds/index.md`):**
implemented as designed. Stage 12 now writes one `application.md` per
variant with `## [question_id] ...`-tagged headings per question;
`scripts/run_judges.py` parses those headings back into a
`{question_id: text}` map deterministically (code-side, not left to the
judge to infer) and fails loudly if the headings found don't exactly
match `form_questions.json`'s ids — same validate-early pattern as the
existing `component_scores`/`question_scores` key checks. Applies from
gen4 onward; gen1–3 stay in the old per-question-file format (already
judged, not reprocessed). See `data_schemas.md` and design doc Stage 12.

**Still open:**
- Whether the judge schema itself needs simplifying (fewer scored
  fields, or splitting one mega-call into smaller calls per section) vs.
  just continuing to raise token budgets/streaming as symptoms recur —
  the single-document format doesn't address this half.
- Whether the single-document format actually reduces cross-answer
  repetition in practice — untested hypothesis, worth checking against
  gen4's real output once drafted, not assumed from the design alone.

---

## 2026-09-07 — Judge-output key validation added; variant-count default flipped (backlog #3, part of #2)

**Resolved — #3 (judge-output key validation):** `scripts/run_judges.py`
now validates `component_scores`/`question_scores` keys against the
actual ids in `jd_components.json`/`form_questions.json` (exact set
match, both extra and missing ids reported) in the same retry loop as
the JSON-syntax/required-key checks, instead of silently accepting a
near-miss key that `aggregate.py` would then quietly drop. Combined with
the marking guide's existing id-verbatim instruction (Stage 3), this
should both prevent and catch the drift gen1 saw (a duplicate-looking
key, one missing the `mission_` prefix).

**Resolved — variant-count default (part of #2):** design doc §4's
default flipped from "5–10" to "3–4 for a first round, widen only if
`summary.md` shows scores bunched close together" — gen1 defaulted to 7
and 6 of those 7 landed statistically indistinguishable, direct evidence
the top of the range doesn't reliably buy more signal.

**Resolved — #2's other half, `cv_evaluation` decoupling: decided not
to.** Checked the actual gen1 eval files before deciding rather than
reasoning from the design doc's description alone: `cv_evaluation`
scores for the same judge are **not** identical across variants (ranged
3–4 across v01–v07 for `judge_skeptical_senior`, with substantively
different comment wording each time), and one variant's comment
explicitly said the CV read as "consistent with the answers" — direct
evidence the judge was reading the CV in light of that specific essay,
not scoring it in isolation. `cv_evaluation` is also never consumed by
`aggregate.py`'s numeric rollup at all (checked `aggregate.py` directly),
so decoupling would only ever have saved generation cost, never rollup
complexity. Between the now-small marginal cost (post comment-length-cap)
and the real risk of throwing away a genuine cross-referencing signal the
"whole package, not siloed" principle (design doc §1) is supposed to
produce, decoupling isn't worth it. Closing this out as resolved, not
just deferred — the original framing ("re-scores the identical CV") was
itself the thing that turned out to be wrong once checked against real
output.

---

## 2026-09-07 — Judge panel parallelized + concrete comment-length caps (backlog #2)

**Resolved, partially:** `scripts/run_judges.py` now runs its
(variant, judge) calls concurrently via a bounded `ThreadPoolExecutor`
(`MAX_WORKERS = 5`) instead of one call at a time — every call is fully
independent (no shared state), so this cuts wall-clock latency roughly in
proportion to the concurrency level without touching Stage 13's isolation
guarantee (still one script, still no shared context with the drafting
session). Bounded rather than unbounded to avoid tripping the Anthropic
API's per-minute rate limits. Doesn't reduce cost — only latency.

Separately, the marking guide's comment-length cap (previously an
abstract placeholder in `data_schemas.md`) now has concrete starting
defaults: ≤40 words per component/question/CV/style comment, ≤100 words
for the overall narrative. This should reduce both cost (shorter required
output) and — per the gen1 retrospective's #3 finding that malformed JSON
correlated with the longest responses — retry-triggering failures too.

**Still open:**
- `cv_evaluation` still re-scores the identical CV in every judge call of
  a round (not decoupled).
- Default variant count still defaults to the top of the 5–10 range
  rather than starting narrow for a first round.
- No rate-limit backoff/retry added for the concurrency change itself
  (only the existing JSON-parse/required-key retry loop) — worth
  revisiting if `MAX_WORKERS = 5` turns out to still trip rate limits in
  practice.

---

## 2026-09-07 — Pre-judge submission-readiness gate added (backlog #1)

**Resolved:** the gen1 retrospective's #1 finding (no cheap, non-naive
check catching placeholders/leftover notes/near-duplicate answers before
they reach the expensive, isolated judge panel) is addressed. No new
pipeline stage — folded into Stage 13 as an explicit precondition
(design doc, Stage 13) plus a concrete checklist in `CLAUDE.md`
(`## Submission-ready checklist`), and wired into `SKILL.md`'s Step 2
so a real run-cycle actually executes it before `run_judges.py`.
Deliberately kept as a plain agent-run checklist, not a scripted gate —
it's a hygiene pass ("does this file look done"), not a judgment call,
so it doesn't need code or an API call to enforce.

**Still open from the gen1 retrospective:**
- **#2 — cost/latency.** `cv_evaluation` still re-scores the identical CV
  in every judge call of a round; default variant count still defaults to
  the top of the 5–10 range rather than starting narrow.
- **#3 — judge-output reliability.** `component_scores`/`question_scores`
  key validation against the actual JD-component/question ids (vs. just
  JSON-syntax/required-key validation, already fixed) is still unbuilt.

---

## 2026-09-06 — Marking guide + drafting guide added; overclaim scoring simplified

**Raised by Jeremy**, in the session immediately following the gen1
retrospective below, scoping and resolving two of its five findings.

**Resolved this session:**
- **#4 (judge marking guide under-directive)** — addressed by a new
  co-created artifact, `output/marking_guide.md`, produced by a new
  **Stage 3** right after JD/form decomposition (Stages 1–2), before any
  of the personal-context stages run. Contains the rubric anchor, the
  id-verbatim instruction, the `overall_score`→`overall_outcome` decision
  rule, and a comment-length cap. `scripts/run_judges.py` now reads this
  file and fails loudly if it's missing, instead of hardcoding the rubric
  in `SYSTEM_TEMPLATE`.
- **#5 (Stage 12 drafting instructions under-directive)** — addressed by a
  second new artifact, `output/drafting_guide.md`, produced by a new
  **Stage 4** alongside Stage 3. Spells out each form question's
  distinct content boundary and a whole-variant cohesion requirement.
  Every Stage 12 forked variant subagent now reads this file as a fixed
  input, alongside `voice_profile.md`.
- **Separately, `overclaim_risk` was simplified, not expanded.** Jeremy's
  call: treating it as a permanent, separately-scored Stage 13 judge
  dimension was over-engineered relative to the actual risk, now that the
  lesson from the original near-miss is well internalized — and it turned
  out never to have actually been implemented as a judge-record field
  anyway (confirmed by reading `data_schemas.md` and `run_judges.py` — no
  such key existed). The guard is now just Stage 11's existing
  `claims_checklist` (unchanged) plus a plain consistency instruction
  inside the new `drafting_guide.md` (Stage 4) — no judge-record field,
  no separate rubric line. `design/agentic_application_eval_design.md`
  §1, §5, Stage 11, and Stage 13; `CLAUDE.md`; and `README.md` were all
  updated to match.

**Still open, deliberately out of scope this session:**
- **#1 — no pre-Stage-11 quality gate.** Not addressed. A cheap,
  no-API-cost checklist pass (no placeholders, no leftover internal notes,
  no near-duplicate answers within a variant) before Stage 13 runs is
  still unbuilt.
- **#2 — cost/latency.** Partially addressed as a side effect: the
  marking guide's comment-length cap directly targets the biggest
  suspected driver (unbounded per-field judge prose). Not addressed:
  `cv_evaluation` re-scoring the identical CV in every one of a round's
  judge calls, and the practical default variant count for a first round.
- **#3 — judge-output reliability.** The JSON-syntax + required-key retry
  loop (already fixed before this session) is untouched. Still open:
  validating `component_scores`/`question_scores` keys against
  `jd_components.json`/`form_questions.json`'s actual ids and
  retrying/warning on mismatch — the marking guide's id-verbatim
  instruction (Stage 3) should reduce how often this happens, but
  doesn't add the validation code itself.

---

## 2026-09-06 — gen1 pilot retrospective: quality gate, cost, and judge-output reliability

**Raised by Jeremy**, immediately after the first live exploration round
(gen1, 7 variants, JD = Anthropic Partner Manager, Global Health) went
through Stages 11–14 end to end. Deliberately kept at the process/meta
level below — no application content, scores, or judge comments
reproduced here, per the repo's public/private split (README
"Background", design doc §3).

**Headline reaction:** the round "worked" in the sense that all pipeline
stages completed and produced a real numeric ranking + qualitative
synthesis, but the session surfaced three separate problems serious
enough that Jeremy called an end to active running (`/run-cycle`) to
address them before continuing:

### 1. No quality gate before the expensive, isolated judge panel

Stage 13 is deliberately isolated (design doc §1) so its whole value
comes from a naive read — but this run showed that isolation stage was
also catching things a **cheap, in-context, non-naive check could have
caught for free before ever spending judge-panel money**:

- The tailored CV (`cv_tailored.md`) still had an unfilled contact-info
  placeholder, *and* the agent had mistakenly left an inline editorial
  note about that placeholder directly in the CV file content itself
  (rather than in `cv_tailoring_notes.json` or conversation). Every
  single judge call this round was handed that flawed CV, and every one
  of them flagged it — a defect that a basic "is this file actually
  submission-ready" pass would have caught before Stage 13 ran at all,
  not something that needed judge naivety to surface.
- At least one draft variant had a completion problem (heavy duplication
  between two of its four answers) that a basic self-review — "does each
  answer in this variant actually say something distinct from the
  others" — would also have caught for free, without needing an outside
  reader.

**The distinction worth drawing:** Stage 13's isolation is for judgment
calls that specifically require *not having been in the room* (does this
argument land, does this overclaim, is the tone right for a stranger).
Placeholder text, leftover internal notes, and one answer duplicating
another within the same variant are **completion/hygiene problems**, not
judgment calls — the agent doesn't need to be naive to catch them, it
just needs to actually check before handing material to the (expensive)
judge panel. The pipeline currently has no explicit step for this second
category between Stage 12 (drafting) and Stage 13 (judging).

### 2. Cost and time: ~$15 and ~40 minutes for one exploration round

Actual spend for 7 variants × 3 judges = 21 judge calls (plus a handful
of extra diagnostic calls made mid-session while debugging, see below).
Contributing factors, roughly in order of likely impact:

- Each judge call scores all ~39 individual JD components (plus 4
  question scores, a CV evaluation, a style-fidelity check, and a
  free-length overall narrative) with a full prose comment per field —
  the judge system prompt does not currently bound comment length
  anywhere, and in practice judges wrote paragraph-length comments per
  component. This is very likely the dominant driver of both token cost
  and wall-clock latency, not the number of variants or judges per se.
- The domain-expert judge persona runs on a pricier model
  (`claude-opus-5`, vs `claude-sonnet-5` for the other two personas) and
  consistently produced the longest responses of the three (see also
  §3 below — its long-output calls were also the least reliable ones).
- `cv_evaluation` re-scores the identical, unchanged `cv_tailored.md`
  inside every one of the 7×3 = 21 calls this round, even though the CV
  doesn't vary by variant — the design doc already flags this as "minor
  duplication... acceptable as-is" (Stage 13), but that assumption is
  worth revisiting now that cost is a live concern, not a theoretical
  one. Whether it can be decoupled without weakening the "whole package,
  not siloed" holistic-scoring principle (design doc Stage 13) is an
  open question, not a settled one.
- 7 variants for a first exploration round is at the upper end of the
  design doc §4 default range (5–10) — and in this round, 6 of the 7
  variants ended up statistically indistinguishable on overall score
  (all within 0.34 points of each other), with only one variant clearly
  separating from the pack. Design doc §4 already says to *widen* only
  when scores come back close — worth flipping the practical default the
  other way too: *start* narrower (e.g. 3–4) for a first round, and only
  widen if that round's own results show the axes aren't discriminating
  enough, rather than defaulting to the top of the range up front.

### 3. Judge-output reliability

Two distinct failure modes hit this run, both now mitigated in
`scripts/run_judges.py` (retry loop, up to 5 attempts per judge call,
validating both JSON syntax and the presence of every required top-level
key before accepting a result):

- **Malformed JSON** — a judge's response occasionally didn't parse as
  valid JSON. Hit 3 times across ~45 total judge calls this session
  (counting diagnostic reruns), always on long responses, most often
  (not exclusively) the opus-5 domain-expert persona.
- **Schema-incomplete but valid JSON** — one call produced syntactically
  valid JSON that was simply missing a required top-level key
  (`question_scores`) entirely. This class of failure isn't caught by
  JSON-syntax validation alone; `run_judges.py` now also checks that all
  required top-level keys are present and retries if not.
- A couple of judge records also used slightly wrong `component_scores`
  keys (a duplicate-looking key, one missing the `mission_` prefix) —
  doesn't break aggregation (`aggregate.py` silently ignores unmapped
  keys) but is a small further sign that a ~39-item id list is a lot for
  a model to reproduce exactly across a very long response. Not yet
  fixed; a plausible fix is validating `component_scores` keys against
  `jd_components.json`'s actual ids and retrying/warning on mismatch,
  same mechanism as the two fixes above.

**The likely connection between all three findings above:** the fixes
for cost (#2, shorter required comments) and reliability (#3, fewer
long-response failures) point the same direction — the current judge
output schema asks for more free-form prose, across more fields, than
either the budget or the failure rate can comfortably support. Tightening
it is likely to help both problems at once, not just one.

### 4. The judge marking guide itself is under-directive

Jeremy's follow-up point: beyond bounding comment *length* (#2/#3 above),
the marking guide judges are actually handed
(`scripts/run_judges.py`'s `SYSTEM_TEMPLATE`) is thin in a more basic
way — it names the output shape but gives judges almost no calibration
for how to use it consistently:

- No rubric anchor for what a 1 vs. 3 vs. 5 actually means for a
  component score (e.g. "5 = direct, specific, verifiable evidence that
  fully meets this component; 1 = no evidence, or evidence that
  contradicts it") — right now each judge persona is free to calibrate
  its own internal 1–5 scale, which is a plausible contributor to the
  score drift/inconsistency noted above, separate from the pure
  comment-length problem.
- No explicit instruction to use the JD-component ids *verbatim* and
  only those ids — the key-naming drift in #3 above (a duplicate-looking
  key, a missing `mission_` prefix) is exactly the kind of thing a more
  directive instruction ("use exactly these ids, do not invent, rename,
  or duplicate any") would likely prevent outright, not just catch after
  the fact via validation.
- No explicit decision rule connecting `overall_score` to
  `overall_outcome` (`screen_in`/`screen_out`) — right now that mapping
  is left to each judge's own judgment call with no stated threshold or
  criteria, which makes the outcome label less useful as a signal than
  it could be.

### 5. Draft generation needs to be more directive per-question and about whole-variant cohesion

Related to #1, but distinct: the gap isn't only that nothing *checks*
for intra-variant duplication after the fact (a gate, #1 above) — it's
that Stage 12's instructions to each forked subagent don't clearly
*specify* what each of the four questions is actually for, so a subagent
has no positive spec to draft against in the first place. Right now each
question gets a loose one-line hint (e.g. "cover the AI X-ray build...")
rather than an explicit content boundary. Worth making the design doc (or
CLAUDE.md) directive about:

- What distinct communicative job each form question does in a
  well-formed application — what belongs in "describe your AI fluency"
  vs. "describe your low-resource experience" vs. "why do you want to
  work here" vs. the open-ended cover-letter field, stated clearly enough
  that a subagent can tell whether a paragraph belongs in this answer or
  a different one before it drafts it, not just be told not to duplicate
  after the fact.
- An explicit whole-variant cohesion requirement: the four answers (plus
  the CV) should read as one coherent application making a coordinated
  case, each answer doing a distinct job, with consistent claims across
  all of them — stated as a drafting instruction up front, not only
  checked for afterward by a gate.
- This is a genuine gap the gen1 round exposed directly: one variant's
  own why-Anthropic and AI-fluency answers ended up substantially
  duplicating each other, which a clearer per-question spec at drafting
  time would likely have prevented, independent of whatever gate also
  catches it later.

### Not yet decided — options to consider when this gets scoped properly

- Add an explicit, cheap (no API cost) pre-Stage-11 quality gate: a fixed
  checklist the agent runs against `cv_tailored.md` and every drafted
  variant before Stage 13 is allowed to run (no placeholder tokens, no
  internal notes/meta-commentary left in output content, word-count
  guidance respected, no near-duplicate content between a variant's own
  answers). Needs a home — a new short design doc subsection (Stage 12.5?
  or folded into Stage 12/13's existing text) plus an explicit "what does
  a submission-ready draft/CV actually look like" checklist somewhere
  concrete (CLAUDE.md or the design doc), not left to be reconstructed
  from judgment each session.
- Tighten Stage 13's judge system prompt to bound comment length per
  field (e.g. one sentence per component, a fixed short cap on the
  overall narrative instead of unrestricted length) — likely the single
  highest-leverage change for both cost and reliability.
- Revisit the default variant count guidance in design doc §4 to
  explicitly favor starting narrow and widening only on a demonstrated
  signal, rather than defaulting to the top of the 5–10 range.
- Add `component_scores` key validation (against `jd_components.json`'s
  actual ids) to the same retry loop already added for JSON-syntax and
  required-key validation in `scripts/run_judges.py`.
- Open question, not yet resolved: whether `cv_evaluation` can be
  decoupled from the per-variant judge call (scored once per judge
  instead of once per variant) without weakening Stage 13's "whole
  package, not siloed" holistic-scoring principle.
- Make the judge marking guide itself more directive (#4): add a scoring
  rubric anchor per point on the 1–5 scale, an explicit instruction to
  use JD-component ids verbatim with no renaming/inventing, and a stated
  decision rule connecting `overall_score` to `overall_outcome` — likely
  belongs in `scripts/run_judges.py`'s `SYSTEM_TEMPLATE`, possibly with
  the rubric anchor itself documented in the design doc or
  `data_schemas.md` so it's not buried only in the prompt string.
- Make Stage 12's drafting instructions more directive per question and
  about whole-variant cohesion (#5): a clear, positive content spec for
  what each form question is for (not just what to avoid duplicating),
  plus an explicit cohesion requirement that all four answers plus the
  CV read as one coordinated application — likely belongs in the design
  doc's Stage 12 section and/or CLAUDE.md, since it's instruction content
  every future drafting fork needs, not just a run-cycle sequencing
  detail.

---

**Parked, not a backlog item:** the question of durable personal/career
info vs. per-application output (whether facts Jeremy supplies mid-run,
e.g. answering a coverage-gap question in the Stage 8 interview, should
ever persist across applications instead of staying scoped to one run's
`output/`) was raised 2026-09-06 and demoted here on 2026-09-07 — a stray
future idea, not something being tracked toward a decision. See design
doc §3 for the one-line pointer.
