# Backlog — open process/design issues from live runs

Not a design doc, not prescriptive — unresolved issues, confusions, or
possible improvements noticed while running the pipeline for real.
Resolved items get folded into the design doc / `history_and_rationale.md`
and removed from here rather than kept as a changelog. Newest at the top.

---

## 2026-09-07 — Recognisable AI tone/style persists despite voice_profile.md; humanizing approach deferred

**Raised by Jeremy**, on first read of gen3 v01: even with
`voice_profile.md` (Stage 10) informing drafting, output still reads with
recognisable AI tone, not genuinely his voice. A dedicated "humanizing"
skill built from curated real-vs-AI writing examples was floated.

**Decision: deferred.** Prioritized fixing `q_why_anthropic` via a
dedicated interview instead (see `rounds/gen3/direction.md`).

**Options if picked up later:** name the actual recurring tics (em-dash
pileups, triadic phrasing, "it's not just X, it's Y") directly in
`voice_profile.md`/`drafting_guide.md` as a lightweight first pass; build
the dedicated skill only if that's not enough. Worth checking against
real gen4 output first — some of it may have resolved as a side effect of
the interview/repetition fixes.

---

## 2026-09-07 — Judge schema may need simplifying

Raised after gen2's judge panel needed `max_tokens` raised 16k→32k
(judges were silently dropping later-enumerated scores in a 26-item
list) and a switch to streaming mode to avoid the SDK's non-streaming
duration limit. Both were reactive patches, not a fix to the underlying
cause: the judge schema asks for more free-form prose, across more
fields, than the budget or failure rate comfortably supports.

**Still open:** whether the schema itself needs simplifying (fewer scored
fields, or splitting into smaller per-section calls) rather than
continuing to raise token budgets as symptoms recur.

---

**Parked, not a backlog item:** whether durable personal/career info
(facts supplied mid-run, e.g. answering a coverage-gap question in the
Stage 8 interview) should persist across applications instead of staying
scoped to one run's `output/` — raised 2026-09-06, demoted here
2026-09-07 as a stray future idea, not something being tracked toward a
decision. See design doc §3 for the one-line pointer.
