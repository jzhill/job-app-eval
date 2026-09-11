# History and rationale

The "why" behind decisions the main design doc now states as one-liners.
Organized by topic; for a chronological log of live-run findings, see
[`backlog.md`](backlog.md).

---

## Naivety vs. context {#naivety-vs-context}

The original manual pilot's key finding: a fresh, context-free reader
catches things a familiar one won't — the overclaim near-miss (below)
surfaced only via an independent, blind judge call. That's a property of
*not having been in the room*, not of routing through the API per se.
Everywhere else — itemizing a posting, tagging context, tailoring a CV,
choosing draft angles — benefits from full context, a clarifying
question, and working through material with Jeremy directly, not a blind
isolated call.

**The organizing question for any stage:** not "does this need an LLM
call" but "does this stage's value depend on the executor not having been
part of the conversation that produced what it's working on." Only Stage
13 answers yes — draft generation (Stage 12) needs independence *between
variants* (solved by forked subagents), not isolation from the session.

Jeremy stays in the loop at Stages 7, 8, and 15 by design — since most of
the pipeline is direct conversation, these are simply the moments within
it where the agent should stop and check in, not separate review steps
bolted on after.

---

## Overclaim guard {#overclaim-guard}

A real overclaim — more direct/solo credit for collaborative work than
was accurate — made it through several manual drafting rounds before an
independent read caught it (see README "Background"; not repeated here
since this doc covers general pipeline behavior, not one application's
content).

**Original design:** a permanent, separately-scored Stage 13 judge
dimension (`overclaim_risk`), since only an isolated naive reader had
caught the original miss.

**Revised:** dropped as a separate judge score. Jeremy has internalized
the lesson, and two cheap checks cover it instead: Stage 11's
`claims_checklist` (every CV claim traced to a source fragment, scored
1–5) and Stage 4's drafting-guide consistency instruction (essay claims
can't exceed what the CV/tagged context support). `origin` tagging (Stage
7) exists partly to serve this: a claim about Jeremy's own experience may
only trace to an `essay_response` or interview-derived fragment, never an
`external_reference` — something he merely read about the employer can't
support a personal claim.

---

## JD/form intake: direct paste + itemize/verify, not fetch+verify

An earlier version fetched the job-posting URL and cross-checked
itemization with a second automated call. Cut in favor of direct human
paste — no LLM in that path means no risk of silent paraphrasing on the
way in, and a live human check is at least as reliable as a second agent
call.

The itemize/verify checkpoint stays regardless of *how* itemizing
happens: an LLM can quietly compress or drop a bullet, and since every
downstream score traces back to `jd_components.json`/`form_questions.json`,
an unfaithful itemization poisons everything after it. The first live run
caught genuine omissions this way (a dropped location line, truncated
clauses), confirming the checkpoint's value independent of mechanism.

Context Mapping (Stage 7) is a harder checkpoint than the original
design's version: Jeremy is approving an LLM's interpretation of his own
words, not his own writing — a harder review. The agent should flag
low-confidence mappings for priority review so a live conversation
doesn't get rubber-stamped the way a cold file read wouldn't.

---

## Voice profiling is one-shot, not iterative

`output/voice_profile.md` (Stage 10) is built only from corrected source
text, never raw dictated/transcribed originals — several earlier fixes
(subject-verb agreement, dropped words, broken parallelism) were
transcription artifacts, not style, and shouldn't be encoded as if they
were. Interview quotes (Stage 8) get no exemption — still fair game for
reuse, but need the same light grammar pass first. Compelling content and
clean prose are different axes.

Style-matching is a one-time distillation at generation time, not an
iterative target: "regenerate until style score is high" tends to
converge toward near-verbatim reuse of source phrasing, defeating the
point of producing genuine variations. `style_fidelity` (Stage 13) exists
only to catch drift toward generic AI-assistant phrasing and triggers one
targeted regeneration, never a full re-optimization pass.

---

## Repo structure and the public/private line

An earlier version drew the line at "raw input private, generated
artifact public" — reasoning that files like `jd_components.json` just
reproduce public posting text. That missed that most generated output
(draft text, judge scores, the tailored CV) *is* the application's
substance and strategy, not a repackaging of public information. Both
`input/` and `output/` are gitignored, full stop.

The repo stays single-application/flat rather than adopting
`applications/<slug>/` scaffolding — revisit once a second real
application shows what actually needs sharing vs. per-application.

---

## Variant count: narrower than the original design

Default exploration-round variant count was originally 12–16; cut to
5–10 per Jeremy's goal of spending less time agonizing over text rather
than maximizing exploration breadth. The gen1 pilot (7 variants) then
showed most landing statistically indistinguishable on overall score —
evidence for starting narrower still and widening only on a demonstrated
signal (see `backlog.md`'s gen1 retrospective).

---

## Judge diversity mechanics

Run 3–5 judges per variant, not clones of one persona: vary the
system-prompt persona, and use a different model than the generator for
at least one judge to reduce self-preference bias. Varying temperature
was dropped — the Messages API has no such parameter; persona and model
are the real diversity levers.

`cv_evaluation` re-scores `cv_tailored.md` fresh per variant even though
the file itself doesn't vary. This looked like pure duplication worth
cutting for cost, but real gen1 output showed scores/comments aren't
actually identical across variants — a judge's read of the CV shifts with
which essay accompanies it, per the "whole package, not siloed" principle
— and the field is never consumed by `aggregate.py`'s numeric rollup
anyway. Decided not to decouple (see `backlog.md`, 2026-09-07).

---

## Sniff check and iteration

Stage 15 expanded beyond just reading results: it now also produces
`output/rounds/genN/direction.md` (commentary, retained phrases, explicit
mode choice for the next round) — the ground-truth check a synthetic
judge panel can't do alone. In the original manual process, an overclaim
went unflagged by the eval agent and was only caught by Jeremy's own
read.

Stage 16 is deliberately not a fully automatic mutation loop. Automatic
mutation without a human approval step is a reasonable future feature
once the rubric and judge panel have proven reliable over more rounds —
not needed for v1.

---

## Folder-vs-single-file inputs

Several inputs (`input/essay/`, `input/cv/`, `input/interview_transcripts/`,
`input/past_drafts/`) are folders taking any number of files rather than
one canonical file:

- **`input/essay/`** — free-writing often happens across sittings, or a
  fragment gets added without a decision about which document it belongs
  in. Originally kept strictly separate from `input/past_drafts/` on the
  assumption essay content is always rough and voice profiling needs only
  corrected text. **Corrected:** that's a default, not a rule — a
  carefully written, already-proofread essay is both content *and* voice
  material. The real criterion is proofread status (ask if unclear), not
  folder identity.
- **`input/cv/`** — a generic CV and one already partly tailored for a
  similar role often each carry detail the other lacks; dropping several
  versions in lets the agent reconcile across them rather than requiring
  a manual merge first. (`.docx` isn't read directly — extract text first
  via `_common.py`'s `read_doc_text(path)`.)
- **`input/interview_transcripts/`** — not limited to one round, and
  covers a conversation held on Jeremy's own initiative, independent of
  this pipeline. Ingestion doesn't require that a brief was generated by
  this session first.
