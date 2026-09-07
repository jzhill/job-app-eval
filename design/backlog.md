# Backlog — process/design issues raised during live runs

Not a design doc, not prescriptive — a running log of issues, confusions,
or possible improvements noticed while actually running the pipeline
end-to-end. Revisit deliberately (scope, decide, then fold into the
design doc or data schemas if adopted) rather than acting on these
mid-cycle. Newest entries at the top.

---

## 2026-09-06 — gen1 pilot retrospective: quality gate, cost, and judge-output reliability

**Raised by Jeremy**, immediately after the first live exploration round
(gen1, 7 variants, JD = Anthropic Partner Manager, Global Health) went
through Stages 9–12 end to end. Deliberately kept at the process/meta
level below — no application content, scores, or judge comments
reproduced here, per the repo's public/private split (README
"Background", design doc §3).

**Headline reaction:** the round "worked" in the sense that all pipeline
stages completed and produced a real numeric ranking + qualitative
synthesis, but the session surfaced three separate problems serious
enough that Jeremy called an end to active running (`/run-cycle`) to
address them before continuing:

### 1. No quality gate before the expensive, isolated judge panel

Stage 11 is deliberately isolated (design doc §1) so its whole value
comes from a naive read — but this run showed that isolation stage was
also catching things a **cheap, in-context, non-naive check could have
caught for free before ever spending judge-panel money**:

- The tailored CV (`cv_tailored.md`) still had an unfilled contact-info
  placeholder, *and* the agent had mistakenly left an inline editorial
  note about that placeholder directly in the CV file content itself
  (rather than in `cv_tailoring_notes.json` or conversation). Every
  single judge call this round was handed that flawed CV, and every one
  of them flagged it — a defect that a basic "is this file actually
  submission-ready" pass would have caught before Stage 11 ran at all,
  not something that needed judge naivety to surface.
- At least one draft variant had a completion problem (heavy duplication
  between two of its four answers) that a basic self-review — "does each
  answer in this variant actually say something distinct from the
  others" — would also have caught for free, without needing an outside
  reader.

**The distinction worth drawing:** Stage 11's isolation is for judgment
calls that specifically require *not having been in the room* (does this
argument land, does this overclaim, is the tone right for a stranger).
Placeholder text, leftover internal notes, and one answer duplicating
another within the same variant are **completion/hygiene problems**, not
judgment calls — the agent doesn't need to be naive to catch them, it
just needs to actually check before handing material to the (expensive)
judge panel. The pipeline currently has no explicit step for this second
category between Stage 10 (drafting) and Stage 11 (judging).

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
  duplication... acceptable as-is" (Stage 11), but that assumption is
  worth revisiting now that cost is a live concern, not a theoretical
  one. Whether it can be decoupled without weakening the "whole package,
  not siloed" holistic-scoring principle (design doc Stage 11) is an
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
that Stage 10's instructions to each forked subagent don't clearly
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
  variant before Stage 11 is allowed to run (no placeholder tokens, no
  internal notes/meta-commentary left in output content, word-count
  guidance respected, no near-duplicate content between a variant's own
  answers). Needs a home — a new short design doc subsection (Stage 10.5?
  or folded into Stage 10/11's existing text) plus an explicit "what does
  a submission-ready draft/CV actually look like" checklist somewhere
  concrete (CLAUDE.md or the design doc), not left to be reconstructed
  from judgment each session.
- Tighten Stage 11's judge system prompt to bound comment length per
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
  instead of once per variant) without weakening Stage 11's "whole
  package, not siloed" holistic-scoring principle.
- Make the judge marking guide itself more directive (#4): add a scoring
  rubric anchor per point on the 1–5 scale, an explicit instruction to
  use JD-component ids verbatim with no renaming/inventing, and a stated
  decision rule connecting `overall_score` to `overall_outcome` — likely
  belongs in `scripts/run_judges.py`'s `SYSTEM_TEMPLATE`, possibly with
  the rubric anchor itself documented in the design doc or
  `data_schemas.md` so it's not buried only in the prompt string.
- Make Stage 10's drafting instructions more directive per question and
  about whole-variant cohesion (#5): a clear, positive content spec for
  what each form question is for (not just what to avoid duplicating),
  plus an explicit cohesion requirement that all four answers plus the
  CV read as one coordinated application — likely belongs in the design
  doc's Stage 10 section and/or CLAUDE.md, since it's instruction content
  every future drafting fork needs, not just a run-cycle sequencing
  detail.

---

## 2026-09-06 — Durable personal/career info vs. per-application output

**Raised by Jeremy**, during Stage 5 follow-up (interrogating
`tagged_context.json` coverage gaps).

**The issue:** it's not yet clear how `tagged_context.json`,
`external_references.md`, `input/essay/`, `output/interview_report.md`,
and `input/cv/` actually relate to each other as a system — specifically,
whether facts about Jeremy's own career/experience that surface *during*
one pipeline run (e.g. answering a coverage-gap question in the Stage 6
interview) get captured anywhere durable, or only live inside that one
run's output.

Right now the honest answer is: only inside that run. `output/` is fully
gitignored, and the repo is deliberately kept single-application/flat
(design doc §3: "Revisit once a second real application shows what
actually needs to be shared vs. per-application."). So a fact Jeremy
supplies to fill a coverage gap for *this* application has no defined
path to becoming an input for a *future* application's run — each run
rebuilds its picture of Jeremy from `input/essay/` + `input/cv/` +
whatever interview happens that round, with nothing that persists as a
standing "about me" corpus across applications.

**Also noticed in the same session:** the pipeline stages read as fairly
linear/checkpoint-based in the design doc, but live usage this cycle
needed to loop back and amend an already-reviewed stage (adding new
fragments to `tagged_context.json` after Stage 5 was nominally "approved,"
in response to coverage-gap follow-up) rather than only ever moving
forward. Worth considering whether the design doc should acknowledge this
more explicitly, or whether it's already implied clearly enough by "agent
in conversation" execution.

**Not yet decided — options to consider when this gets scoped properly:**
- A durable, cross-application "experience bank" (a new top-level folder,
  outside `output/`'s per-run gitignore treatment) that future runs could
  read as an additional standing input, alongside the per-application
  `input/essay/` etc.
- Or: treat this as already covered by `input/past_drafts/` /
  `input/cv/` accumulating informally over time, with no new mechanism
  needed.
- Directly tied to design doc §3's own open question about what should
  be shared vs. per-application once a second real application exists to
  learn from.
