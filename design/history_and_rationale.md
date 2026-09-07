# History and rationale

This is the "why" that used to live inline in
[`agentic_application_eval_design.md`](agentic_application_eval_design.md)
before that document was cut down to focus on *what the pipeline does*.
Nothing here changes current behavior — it's the decision history and
extended reasoning behind decisions the main doc now only states as
one-liners. Organized by topic, not chronologically; for a chronological
log of live-run findings and in-flight decisions, see
[`backlog.md`](backlog.md) instead.

---

## Naivety vs. context {#naivety-vs-context}

The single highest-value finding from the original manual pilot was that
a fresh, context-free reader catches things a familiar one won't — the
overclaim near-miss (below) surfaced only once an independent judge call,
blind to the drafting process that produced the text, was run against it.
That's not a property of routing a call through the Anthropic API as
such; it's a property of *not having been in the room*. Everywhere else
in this pipeline, the opposite is true — itemizing a job posting, tagging
context, tailoring a CV, choosing genuinely distinct angles for draft
variants — all benefit from an agent that has full context, can ask a
clarifying question mid-task, and can work through material with Jeremy
directly, rather than firing one blind API call and hoping the JSON comes
back parseable.

An earlier version of this design read the choice to script Stage 12/13
as being about the API call itself being "a clean, scriptable, loggable
unit" — a real but secondary benefit that doesn't actually require
isolation from context. Once that was made explicit, draft generation
(Stage 12) belonged with the rest of the in-context stages, not with
judging. Stage 12 looked like a plausible second candidate for isolation
at first pass (variant diversity needs independence too) — but the actual
requirement there is independence *between variants*, not independence
from the session, which is why forked subagents solve it without needing
to route generation back through the Anthropic API.

**The organizing question when adding or reconsidering any stage:** not
"does this need an LLM call" (almost everything here does) but "does this
stage's value depend on the executor not having been part of the
conversation that produced what it's working on." Only Stage 13 answers
yes.

The human (Jeremy) stays in the loop at Stages 7, 8, and 15 by design, not
as a fallback — and since most of the pipeline runs as direct
conversation rather than script-then-review, these are simply the moments
within that conversation where the agent should stop and check in, not
separate review steps bolted on afterward.

---

## Overclaim guard {#overclaim-guard}

A real overclaim made it through several manual drafting rounds during
the original pilot before being caught — a claim of more direct/solo
ownership over a piece of collaborative work than was accurate (see
README "Background" for the actual story; deliberately not repeated in
the main design doc, since that document describes general pipeline
behavior, not one application's specific content).

**Original design:** `overclaim_risk` was treated as a permanent,
separately-scored Stage 13 judge dimension, on the theory that the near
-miss was caught by an isolated, naive reader rather than by care alone —
still true in general (it's the reason Stage 13 stays isolated for tone/
argument/framing judgment calls) — and that self-review had already
failed once, so only Stage 13's naive panel could be trusted as the real
backstop.

**Revised, current design:** that guard no longer includes a separate
Stage 13 judge score. Jeremy has since internalized this particular
lesson well enough, and the drafting-time consistency check (Stage 4) +
CV claims checklist (Stage 11) are cheap enough, that a dedicated scored
judge dimension wasn't earning its cost and complexity. The guard is now
two plain checks instead: Stage 11's `claims_checklist` (every CV claim
traced to a source fragment, scored 1–5 for overclaim risk) and Stage 4's
drafting-guide instruction (essay claims can't exceed what the CV/tagged
context support). Simplify rather than keep elaborating a guard against a
mistake that's now unlikely to recur unnoticed.

Also worth keeping: a mission/role-specificity signal as part of Stage
13's scoring — already covered structurally via `component_scores`'
`mission_signals` category (Stage 1) — one of the two highest-value
findings from the original pilot, alongside overclaim risk.

`origin` tagging (Stage 7) exists partly to serve this guard: CV Tailoring's
`claims_checklist` may only trace a claim about Jeremy's own experience to
an `essay_response` or interview-derived fragment, never to an
`external_reference` fragment — a claim about Jeremy cannot be supported
by something he merely read. External references (Stage 6) generalize
something that already happened ad hoc in the manual process (Anthropic's
mission language and a partnership announcement were grounded via live
web search of Anthropic's own public materials, not invented) into a
repeatable stage — but that material is never treated as a claim about
Jeremy, only as color/grounding for how the application talks about the
employer.

---

## JD/form intake: direct paste + itemize/verify, not fetch+verify

An earlier version of this design had the pipeline fetch the job-posting
URL and capture it verbatim via a script/agent, then cross-check the
itemization with a second automated call. Cut in favor of a direct human
paste (Jeremy copies the raw text himself) because that removes the
fetch-fidelity risk entirely — a direct paste has no risk of an LLM
silently paraphrasing or summarizing on the way in, since there's no LLM
in that path at all — and a live human check against material he already
has open is at least as reliable as a second agent call, now a real-time
conversation rather than a rerun-and-reread cycle.

The itemize/human-verify checkpoint itself (Stages 1–2) stays regardless
of *how* itemizing happens, because the risk it guards against is general:
an LLM asked to itemize can quietly compress or drop a bullet, and since
every downstream score traces back to `jd_components.json`/
`form_questions.json`, an unfaithful itemization poisons everything after
it. The first real run of this stage against a live JD posting caught
genuine omissions this way — a dropped location line, a few
ellipsis-truncated clauses — confirming the checkpoint's value
independent of the mechanism (script → in-context agent) that produced
the itemization.

Context Mapping (Stage 7) is a harder checkpoint than the original
design's version for a related reason: Jeremy is no longer approving his
*own* tagging, he's approving an LLM's interpretation of his own words —
a harder review than approving his own writing. The agent should flag
low-confidence mappings for priority review as it presents them, so this
checkpoint doesn't get rubber-stamped just because it's now a live
conversation rather than a cold read of a file.

---

## Voice profiling is one-shot, not iterative

Build `output/voice_profile.md` (Stage 10) only from corrected source
text — proofread drafts and any additional writing samples Jeremy
supplies, never raw dictated/transcribed originals. Several fixes applied
earlier in the manual process (subject-verb agreement, dropped words,
broken parallelism) were transcription artifacts, not style, and
shouldn't be encoded into the profile as if they were.
`output/interview_report.md`'s verbatim quotes (Stage 8) get no exemption
from this rule — still fair game for direct reuse in drafting, but need
the same light grammar pass as any other sample before feeding Stage 10.
Compelling content and clean prose are different axes; one doesn't imply
the other.

Style-matching is treated as a one-time distillation applied at
generation time, not an iterative optimization target: an iterative
"regenerate until style score is high" loop tends to converge toward
near-verbatim reuse of source phrasing, which defeats the purpose of
producing genuine variations. `style_fidelity` (Stage 13) exists only to
catch drift toward generic AI-assistant phrasing, and triggers a single
targeted regeneration, never a full re-optimization pass — regardless of
who performs the distillation, it's Stage 13's judge panel, still
scripted and still naive, that enforces this.

---

## Repo structure and the public/private line

An earlier version of this design drew the public/private line at "raw
input is private, generated artifact is public," on the reasoning that
generated files like `jd_components.json` just reproduce public posting
text. That missed that most of what actually gets generated — draft essay
text, judge scores and critiques, the tailored CV — *is* the application's
substance and strategy, not just a repackaging of public information, and
shouldn't be sitting in a public repo regardless of whether any single
field in it counts as "personal data." Both `input/` and `output/` are
gitignored, full stop.

The repo stays single-application/flat rather than adopting
`applications/<slug>/` scaffolding — revisit once a second real
application shows what actually needs to be shared vs. per-application.

---

## Variant count: narrower than the original design

Default variant count for an exploration round was originally 12–16;
cut to 5–10, per Jeremy's stated goal of spending less time agonizing
over the text rather than maximizing exploration breadth. The gen1 pilot
round (7 variants) also showed most variants landing statistically
indistinguishable on overall score — a live data point in favor of
starting narrower and widening only on a demonstrated signal, rather than
defaulting to the top of the range up front (see `backlog.md`'s gen1
retrospective).

---

## Judge diversity mechanics

Run 3–5 judges per variant, not clones of one persona: vary the judge
system-prompt persona, and use a different model than the generator for
at least one judge to reduce self-preference bias. An earlier version of
this design also called for varying temperature across judges — dropped,
since the Messages API has no temperature/sampling-randomness parameter
to vary; persona and model are the actual diversity levers now.

`cv_evaluation` scores the same `cv_tailored.md` for every variant in a
round, since the CV isn't varied per-variant — minor duplication across
judge calls, acceptable as-is (revisit if cost becomes a bigger concern —
see `backlog.md`).

---

## Sniff check and iteration: why these exist as separate, expanded steps

Stage 15 is an expansion of the original design: beyond just reading
results, it now also produces `output/rounds/genN/direction.md` —
freeform commentary, plus explicitly retained phrases or points, plus
Jeremy's explicit choice of mode for the next round. This is the
ground-truth check a synthetic judge panel can't do on its own — in the
original manual process, a calibration/validation overclaim went
unflagged by the eval agent and was only caught by Jeremy's own read.

Stage 16 is deliberately not a fully automatic genetic/mutation loop.
Automatic mutation without a human approval step is a reasonable future
feature once the rubric and judge panel have proven reliable over more
rounds — not needed to get value out of v1.

---

## Folder-vs-single-file inputs

Several inputs (`input/essay/`, `input/cv/`, `input/interview_transcripts/`,
`input/past_drafts/`) are folders taking any number of files, any
filename, rather than one canonical file each:

- **`input/essay/`** — the same free-writing often happens in more than
  one sitting, or Jeremy drafts a fragment somewhere and wants to add it
  later without deciding whether it belongs in "the" essay response or a
  separate note. A folder removes that decision. Kept separate from
  `input/past_drafts/` (Stage 10's voice-sample folder): essay content
  here is expected to be rough, unedited freewriting, while voice
  profiling depends on reading only corrected text — mixing the two
  folders would make it easy to accidentally feed uncorrected prose into
  the voice profile.
- **`input/cv/`** — a generic CV and a version already partly tailored for
  a similar role often each carry detail the other lacks. Dropping
  several versions in lets the agent reconcile across them — pulling in a
  detail from the generic one that a prior tailoring pass dropped, for
  instance — rather than forcing Jeremy to manually merge them first.
  (Practical note: this agent's file-reading tools handle plain text,
  Markdown, and PDF directly, but not `.docx` — for a Word CV, extract
  text first with `_common.py`'s `read_doc_text(path)` helper, run via a
  one-off command.)
- **`input/interview_transcripts/`** — not limited to one round, and
  covers a conversation Jeremy already had on his own initiative,
  independent of this pipeline. Nothing about ingestion requires that a
  brief was generated by this session first.
