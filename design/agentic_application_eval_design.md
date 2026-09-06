# Design: Agentic Job-Application Drafting & Evaluation Pipeline

A small repo, operated as a live Claude Code session, that automates a
manual workflow prototyped by hand in a browser Claude session. High level
process: JD- and form-referenced draft generation, informed by a one-time
distilled voice profile and a reflective interview, → structured
multi-judge evaluation of the whole application package → aggregated
feedback → human-directed iteration.

This is v1 of a design meant to generalize beyond a single application
(originally Anthropic's Partner Manager, Global Health role). The repo
itself stays single-application/flat for now (see §3) — the generalization
is in the pipeline's shape, not yet in the folder structure.

This document is meant to be read start to finish by a human. Exact JSON
shapes for generated files are kept out of the main text and collected in
[`data_schemas.md`](data_schemas.md) instead, linked from wherever a stage
below produces one — those shapes are unchanged by anything in this
document, since they describe *what* gets produced, not *how*.

---

## 1. Core principle

**Everything is scored against the job description, not against a generic
rubric.** The JD is decomposed once, up front, into labeled components.
Every downstream score — quantitative and qualitative — is tied back to one
or more of those components. This is what turns "does this sound good" into
"does this answer what the employer actually asked for."

**A second principle governs how each stage is executed: naivety is a
resource, and it's scarce.** The single highest-value finding from the
original manual pilot was that a fresh, context-free reader catches things
a familiar one won't — the overclaim near-miss (§5) surfaced only once an
independent judge call, blind to the drafting process that produced the
text, was run against it. That's not a property of routing a call through
the Anthropic API as such; it's a property of *not having been in the
room*. Everywhere else in this pipeline, the opposite is true — itemizing a
job posting, tagging context, tailoring a CV, choosing genuinely distinct
angles for draft variants — all benefit from an agent that has full
context, can ask a clarifying question mid-task, and can work through
material with Jeremy directly, rather than firing one blind API call and
hoping the JSON comes back parseable.

So execution splits cleanly along this line: **Stage 11 (the judge panel)
is the only stage that must run as an isolated, scripted Anthropic API
call, because it's the only stage whose value depends on the executor not
sharing context with whatever produced the material it's judging. Every
other stage is performed directly by the Claude Code agent operating in
this repo, in conversation with Jeremy** — reading input files, reasoning
with full context, writing the same output artifacts this design
specifies, and asking questions rather than reaching a block. (An earlier
version of this design read the choice to script Stage 10/11 as being
about the API call itself being "a clean, scriptable, loggable unit" — a
real but secondary benefit that doesn't actually require isolation from
context. Once that was made explicit, draft generation belonged with the
rest of the in-context stages, not with judging — see Stage 10 below for
how it stays genuinely exploratory once moved in-context.)

The human (Jeremy) stays in the loop at three points by design, not as a
fallback — and now, since most of the pipeline runs as direct conversation
rather than script-then-review, these are simply the moments within that
conversation where the agent should stop and check in, not separate
review steps bolted on afterward:
1. after context mapping, approving the agent's tagging of his own raw
   material against JD components (§ Stage 5) — a harder review than
   approving his own writing, since he's now checking someone else's
   interpretation of his words, not his own;
2. as an active participant in the reflective interview itself (§ Stage 6),
   not a passive input source;
3. after each evaluation round, doing the "sniff test" on top candidates and
   supplying direction before the next generation runs (§ Stage 13).

The agent drafts and prepares; a naive panel scores; neither decides alone.

---

## 2. Pipeline stages

```
1.  JD Decomposition            [agent, in-context]         → output/jd_itemised.md → output/jd_components.json
2.  Form Decomposition          [agent, in-context]         → output/form_itemised.md → output/form_questions.json
3.  Essay Response Capture      [Jeremy, direct]            → (Jeremy drops free-written material in input/essay/)
4.  External Reference Ingestion [agent, in-context]        → output/external_references.md
5.  Context Mapping             [agent, in-context]         → output/tagged_context.json (+ output/tagged_context.md)
6.  Reflective Interview        [external voice app; brief/ingest by agent, in-context] → output/interview_report.md
7.  Preferences File            [Jeremy, direct]            → (Jeremy writes input/preferences.md directly)
8.  Voice Profiling              [agent, in-context]        → output/voice_profile.md
9.  CV Tailoring                 [agent, in-context]        → output/cv_tailored.md + output/cv_tailoring_notes.json
10. Draft Generation             [agent, in-context; one forked subagent per variant] → output/drafts/genN/vXX/q<question_id>.md + vXX.meta.json
11. Judge Panel Evaluation       [scripted → Anthropic API] → output/evals/genN/vXX_<judge>.json
12. Aggregation                  [agent, in-context; scripts/aggregate.py for the numeric rollup] → output/evals/genN/summary.json + summary.md
13. Human Sniff Check            [Jeremy + agent, in-context, manual] → output/rounds/genN/direction.md
14. Directed Iteration           [agent, in-context]        → output/rounds/gen(N+1)/round_config.json
```

Only Stage 11 is a separate script (`scripts/run_judges.py`, plus the
`_common.py` Anthropic SDK helper it shares with `scripts/aggregate.py`'s
non-LLM number-crunching). Every other stage is executed by the Claude Code
agent directly, following the instructions below, producing the same
artifacts a script would have — so the pipeline can be picked up at any
stage in a fresh conversation, the same way a script could previously be
rerun alone.

---

### Stage 1 — JD Decomposition

**Input:** `input/job_posting.md` — Jeremy copy-pastes the raw text of the
job posting himself, directly from the browser. This replaces an earlier
version of this design that had the pipeline fetch the URL and capture it
verbatim via a script/agent — that added a fetch step, a second
verification agent call, and real token cost to solve a problem a human
copy-paste already solves for free: a direct paste has no risk of an LLM
silently paraphrasing or summarizing on the way in, because there's no LLM
in that path at all. Simplicity first.

**Step 1a — Itemization.** The agent breaks `input/job_posting.md` into a
discrete, numbered list of items — every distinct requirement,
responsibility, sentence, or bullet gets its own item, grouped under
whatever section headers the source page itself used. This is a
structural pass only; it is not yet the four-category semantic pass below.
Output: `output/jd_itemised.md`.

**Step 1b — Human verification.** Jeremy checks `output/jd_itemised.md`
against the actual posting (which he has open, having just pasted from it)
and confirms nothing was dropped, paraphrased, or invented, or tells the
agent directly what to fix. This is now a live exchange, not a
round-trip through a rerun script — the risk it guards against is still
real and still generalizable: an LLM asked to itemize can quietly compress
or drop a bullet, and since every downstream score in this pipeline traces
back to `jd_components.json`, an unfaithful itemization poisons everything
after it. That risk doesn't depend on whether a script or an agent did the
itemizing, which is why this checkpoint stays regardless of execution
mechanism.

**Step 1c — Semantic decomposition.** The verified `output/jd_itemised.md`
is decomposed into `output/jd_components.json`, which sorts everything
into four categories — required qualifications, preferred qualifications,
core responsibilities, and mission signals — with each item keeping a
short id and the exact text it came from. (Exact file shape:
[`data_schemas.md`](data_schemas.md#jd_componentsjson).)

**Reviewed and hand-edited by Jeremy** — a wrong or sloppy decomposition
poisons every downstream score. These four top-level keys
(`required_qualifications`, `preferred_qualifications`,
`core_responsibilities`, `mission_signals`) are also the grouping used for
the section-level rollup in Stage 12 (Aggregation).

---

### Stage 2 — Form Decomposition

**Input:** the same `input/job_posting.md` as Stage 1 in the common case —
many ATS platforms (Greenhouse included; confirmed against a real posting)
render the job description and the application form's fields on one page,
so one paste covers both. If an employer's form truly lives on a separate
page, Jeremy pastes that into `input/job_posting.md` as well (append,
don't create a second file — one human-provided source per application
keeps the input contract simple).

**Step 2a — Itemization** → `output/form_itemised.md` — every
field/question captured as its own item, with whatever prompt text and
stated limit appear on the source page. Same approach as Stage 1a, done by
the agent directly.

**Step 2b — Human verification** → same as Stage 1b: Jeremy checks
`output/form_itemised.md` against the actual form, live, in conversation.

**Step 2c — Structural decomposition** → `output/form_questions.json`,
purely structural facts about the form itself: each question gets an id,
its exact prompt text, any stated word/character limit, and whether it's
required. Deliberately does **not** pre-assign JD components to a
question; that mapping happens at generation time (Stage 10), not here.
(Exact file shape: [`data_schemas.md`](data_schemas.md#form_questionsjson).)

A generated draft references its question by file location, not an
embedded field: `output/drafts/genN/vXX/q_why_anthropic.md`. This keeps
the reference unambiguous and lets Stages 11–12 glob by question id.

---

### Stage 3 — Essay Response Capture

**Input/Output:** Jeremy writes directly into `input/essay/` — any number
of files, any filename, fully unstructured prose. No required headers, no
`[addresses: ...]` tagging. He should write toward the JD loosely —
attending to it, but without forcing himself into per-component or
per-question structure, jumping between experience, motivation, and
reflection in whatever order it comes out. The mapping work belongs to
Stage 5, not to him. There is no separate generated artifact for this
stage — the agent reads every file in `input/essay/` directly; Stage 5
doesn't care whether it's one file or several.

**Why a folder, not a single `essay_response.md`:** the same free-writing
often happens in more than one sitting, or Jeremy drafts a fragment
somewhere and wants to add it later without deciding whether it belongs in
"the" essay response or a separate note. A folder removes that decision —
drop it in, the agent reads all of it. **Kept separate from
`input/past_drafts/`** (Stage 8's voice-sample folder) rather than merged
with it: essay content here is expected to be rough, unedited freewriting,
while voice profiling depends on reading only corrected text (§5) — mixing
the two folders would make it easy to accidentally feed uncorrected prose
into the voice profile.

---

### Stage 4 — External Reference Ingestion

**Input:** `input/external_resources.md` (optional — a plain list of URLs
Jeremy has collected as relevant background, one per line, with an
optional short note) and/or files dropped in `input/external_refs/`
(PDFs etc.). This is material about the external world, not personal
experience.

**Process:** the agent reads each resource directly — fetching URLs from
`input/external_resources.md` with its own web-fetch tool, reading files
under `input/external_refs/` directly — and does a quick, single-pass
digest of each: lightweight, not the multi-step verbatim/verify treatment
JD/form intake gets (§ Stages 1–2), since this is supplementary grounding
material, not a structural document everything else traces back to.
Capture: the source (URL or filename), a concise summary of its key
content, and an optional short note from Jeremy on why he flagged it. Even
without an explicit note, the fact Jeremy selected a given resource is
itself signal about what he finds relevant or compelling.

**Output:** `output/external_references.md` — one entry per resource:

```markdown
## Beneficial Deployments — Gates Foundation partnership announcement
Source: https://...
Summary: <2-4 sentence digest of the actual content>
Why flagged: <Jeremy's note, if given>
```

**Important distinction from `tagged_context.json`:** this material is
never treated as a claim about Jeremy's own experience — only as color,
specificity, and grounding for how the application talks about the
employer. The overclaim guard (Stage 9's `claims_checklist`, Stage 11's
judge `overclaim_risk`) applies only to claims about Jeremy. This
generalizes something that already happened ad hoc in the manual process —
Anthropic's mission language and the Gates Foundation partnership were
grounded via live web search of Anthropic's own public materials, not
invented — into a repeatable stage.

**Downstream use:** feeds Stage 5 (Context Mapping may also tag reference
entries to JD components, alongside personal fragments — see the `origin`
field below), Stage 6 (the interviewer can ask what specifically stood out
about a flagged resource), and Stage 10 (Draft Generation, as grounding
material).

---

### Stage 5 — Context Mapping

**Input:** every file in `input/essay/`, `output/external_references.md`,
`output/jd_components.json`, `output/form_questions.json`.

**Output:** `output/tagged_context.json` — the canonical mapping of
fragments onto JD components and (once available) form questions, with a
confidence field per fragment and an `origin` field distinguishing
personal material from external reference material. A
`output/tagged_context.md` rendering (grouped by JD component, in the same
visual shape the original hand-tagged file used) is produced alongside it
purely for the human checkpoint — Jeremy never edits it directly; he
approves it or kicks back specific fragments for correction, live, in the
same conversation the agent produced it in.

Each fragment records: the source text itself, which JD components and
form questions it supports, how confident the mapping is, and where it
came from — Jeremy's own writing, the interview, or an external reference
(the `origin` field, see below). A separate list flags JD components with
weak or no supporting material yet. (Exact file shape:
[`data_schemas.md`](data_schemas.md#tagged_contextjson).)

**`origin` matters beyond bookkeeping:** CV Tailoring's `claims_checklist`
(Stage 9) may only trace a claim about Jeremy's own experience to an
`essay_response` (or interview-derived) fragment — never to an
`external_reference` fragment, since a claim about Jeremy cannot be
supported by something he merely read.

**This checkpoint is harder than the original design's version.** Jeremy is
no longer approving his own tagging — he's approving an LLM's
interpretation of his own words. The agent should flag low-confidence
mappings for priority review as it presents them, so this checkpoint
doesn't get rubber-stamped just because it's now a live conversation
rather than a cold read of a file. `coverage_gaps` is computed here but
does not gate Stage 6 — it's informational input to it, not a
precondition.

---

### Stage 6 — Reflective Interview

**Purpose:** this is not a rote gap-filling Q&A keyed only to weak JD
coverage. It **always runs**, every round of context-gathering, regardless
of whether Stage 5 found coverage gaps. Its job is broader: a curious,
thoughtful exchange to elicit Jeremy's motivations, ideas, and intentions in
relation to the job — the kind of reflective material that showed up
before only through dialogue, never supplied directly in a CV or a first
draft (e.g. the political-fragility spectrum and data-sovereignty argument
from the original Anthropic process).

**Input:** the interviewing agent needs full context to ask genuinely
relevant, non-generic questions — the JD, `output/jd_components.json`,
`output/tagged_context.json` (including coverage gaps and
external-reference fragments, as hints toward under-explored territory,
not a script to follow), and the CV.

**Output:** `output/interview_report.md` — an organized, annotated
write-up of the exchange (not a raw transcript), with a clearly separated
section of verbatim quotes or passages flagged as particularly compelling
— candidates for direct, unaltered reuse in later drafts. This feeds
forward as its own first-class input to Stage 10, distinct from
`tagged_context.json` — it is not merged back into the tagged-context file.

**Resolved:** verbatim quotes flagged here are still fair game for direct,
unaltered reuse in Stage 10 drafting — that's the whole point of flagging
them. But if the same material is later used as Stage 8 voice-profiling
input, it needs the same light grammar/correction pass as any other
`input/past_drafts/` sample first; interview transcripts get no special
exemption from that rule just because they're compelling. Reflective
material and clean prose are different axes — a quote can be excellent
content and still carry a transcription artifact that shouldn't be read
as "voice."

**Delivery mechanism: the interview conversation itself does not run
inside Claude Code.** Claude Code has no voice interface, and there is no
session handoff between Claude Code and claude.ai/Gemini/ChatGPT's
voice-mode apps — they don't share context, the same way claude.ai's
memory doesn't carry into Claude Code (see project history). The best
setting for this interview is conversational and hands-free (driving,
walking), which points squarely at an external voice-mode app, not this
tool. So the agent's role here is narrower than for every other stage — it
has two jobs, both still performed directly in this session, just bracketing
the external conversation rather than replacing it:

1. **Generate a portable interview brief**, saved to
   `output/interview_brief.md` — a self-contained prompt (since the
   external session starts with zero context, same reasoning as the
   original handover doc) bundling the JD, the relevant
   `output/jd_components.json` entries, `output/tagged_context.json`'s
   coverage gaps, CV highlights, and explicit instructions on interview
   style (curious, thoughtful, not rote Q&A) and the exact output shape
   wanted back (organized report + a separated verbatim-quotes section).
   Jeremy copies this into Claude/Gemini/ChatGPT's voice mode and has the
   actual conversation there.
2. **Ingest the result** into `output/interview_report.md`, normalizing
   whatever shape the external conversation produced into the schema
   above.

**Input for ingestion:** every file in `input/interview_transcripts/` — a
folder, any filename, so it isn't limited to one round. This also covers a
conversation Jeremy already had on his own initiative, independent of
this pipeline: nothing about ingestion requires that a brief was generated
by this session first — dropping a transcript or a set of notes into the
folder and asking the agent to ingest it works the same way regardless of
how the conversation came about. For a genuinely new/follow-up round, the
agent should read `output/interview_report.md` and whatever's already in
`input/interview_transcripts/` before drafting a fresh brief, so the new
brief targets ground that's actually still uncovered rather than
re-asking what's already there.

---

### Stage 7 — Preferences File

**Input/Output:** Jeremy writes directly into `input/preferences.md` —
human-authored, like the material in `input/essay/`, not generated by the
agent. Not
*facts about Jeremy*, but *how he wants the pipeline to weight things*.
Kept distinct from context so it's easy to update without touching the
factual record, and kept **durable across rounds** — per-round tactical
notes belong in `output/rounds/genN/direction.md` (Stage 13), not here, so
this file doesn't accumulate noise round over round or application over
application.

```markdown
# Preferences

- Prioritize argument X as the intellectual centerpiece of the essay — it
  is the strongest, most original idea in the material gathered so far.
- Do not overclaim sole ownership of collaborative work. Frame project Y
  as close collaboration with named partners, not solo execution — this
  is factually accurate and should never be reverted (see README
  "Background" for why this constraint exists).
- Voice: plain, declarative sentences. Avoid stacking more than one
  "big idea" in a closing paragraph.
```

---

### Stage 8 — Voice Profiling

The agent performs a single analysis pass — not a loop — over corrected
source text only — proofread past drafts and any additional writing
samples, **never** raw dictated/transcribed originals, since transcription
artifacts (subject-verb agreement, dropped words, broken parallelism) risk
being encoded as "voice" if the profiling pass runs on unfiltered text. If
it's unclear whether a given sample in `input/past_drafts/` has been
proofread, the agent should ask rather than assume. Output:
`output/voice_profile.md`, a fixed input to every Stage 10 generation call,
not regenerated per variant or per round.

**Guardrail for the judge panel:** a distinct, low-weight `style_fidelity`
check (see Stage 11), separate from content-quality scores, catches drift
toward generic "assistant voice." A failing variant gets a single targeted
regeneration — never a full re-optimization pass. Style-matching is a
one-time distillation applied at generation time, not an iterative
optimization target: an iterative "regenerate until style score is high"
loop tends to converge toward near-verbatim reuse of source phrasing, which
defeats the purpose of producing genuine variations. This guardrail holds
regardless of who performs the distillation — it's Stage 11's judge panel,
still scripted and still naive, that actually enforces it.

---

### Stage 9 — CV Tailoring

The CV was previously static input context only; this stage tailors it per
application.

**Input:** `output/jd_components.json`, `output/tagged_context.json`,
every file in `input/cv/`, `input/preferences.md`.

**Why a folder, not a single `current_cv.*`:** a generic CV and a version
already partly tailored for a similar role often each carry detail the
other lacks. Dropping several versions into `input/cv/` (any format,
any filename) lets the agent reconcile across them — pulling in a detail
from the generic one that a prior tailoring pass dropped, for
instance — rather than forcing Jeremy to manually merge them into one
canonical file before this stage can even start. One practical note: this
agent's file-reading tools handle plain text, Markdown, and PDF directly,
but not `.docx` — for a Word CV, extract the text first with
`_common.py`'s `read_doc_text(path)` helper, run via a one-off command;
there's no longer a script that calls it as a pipeline stage, but the
helper itself still works for this.

**Output:** `output/cv_tailored.md` (reordered/re-emphasized bullets and
summary, same section structure as the source CV) and
`output/cv_tailoring_notes.json` — a record of what changed and why, plus
a claims checklist: every factual claim in the tailored CV is traced back
to a specific context fragment (`origin: essay_response` or an
interview-derived fragment only — never `origin: external_reference`, per
Stage 5), or flagged if it can't be traced. (Exact file shape:
[`data_schemas.md`](data_schemas.md#cv_tailoring_notesjson).)

**Deliberately single-pass, not a variant tournament.** CVs are
factual/structured and lower voice-sensitivity than an essay, so the
overclaim risk (a real, hard-won lesson — see §5) is better guarded
directly via this checklist than explored stylistically via multiple
generations. `overclaim_risk` here uses **the same 1–5 scale** as the
essay's judge-scored `overclaim_risk` (Stage 11), for one consistent
audit trail across both artifacts.

**Doing this in-context doesn't weaken the overclaim guard.** The original
near-miss went through several drafting rounds before an independent,
context-free read caught it — self-review, however careful, already failed
once. That's exactly why `overclaim_risk` is *also* a permanent Stage 11
judge score, not just this checklist: the checklist here is a first pass,
and Stage 11's naive panel is the real backstop, unaffected by who or what
produced the CV it's judging. If anything, an agent working through this
live with Jeremy can flag a questionable claim in the moment ("does this
bullet overstate your role here?") rather than only surfacing it in a JSON
file after the fact — but Stage 11 stays the check that doesn't get to
assume its own work is right.

---

### Stage 10 — Draft Generation

**Input:** `output/jd_components.json`, `output/tagged_context.json`,
`output/interview_report.md`, `output/external_references.md`,
`output/form_questions.json`, `input/preferences.md`,
`output/voice_profile.md`, and the current round's
`output/rounds/genN/round_config.json` (mode + variant count +
carried-forward direction from the prior round, if any — see Stage 14).

**Output:** `output/drafts/genN/vXX/q<question_id>.md` per question, plus
`vXX.meta.json` recording the axis/rationale that produced it and which
model ran the fork that wrote it.

**Generalized from one essay to N questions.** `form_questions.json` may
list one question or several; each variant is one coherent bundle of
answers across *all* questions, generated together so answers don't repeat
or collide with each other.

**Mode-aware**, per `round_config.json`:

- **Exploration mode.** This is where moving generation in-context needed
  real care, not just a straight swap. Exploration mode's value depends on
  genuine independence between variants — it's a hedge across a hypothesis
  space, judged afterward — and a single continuous conversation risks
  quietly collapsing that independence: if all variants get drafted
  inside one throughline with Jeremy, they tend to converge toward
  whatever framing gets settled on mid-session, which turns "exploration"
  into "convergence with extra steps." The design resolves this in two
  parts:
  1. **Axis selection happens in the main session, with Jeremy.** Before
     any drafting starts, the agent proposes a set of genuinely distinct
     strategic/rhetorical bets for this specific round — grounded in what's
     actually distinctive in the material at hand (e.g. "one variant leads
     with the data-sovereignty argument as centerpiece, one leads with the
     field-work narrative, one foregrounds the regulatory-landscape angle")
     rather than a generic combinatorial grid of structural knobs. Jeremy
     can steer this list before generation begins.
  2. **Each variant is drafted by its own forked subagent**, handed the
     full context bundle above plus its one specific axis, and nothing
     else — it does not see the other forks' output. This preserves real
     independence between variants (no cross-contamination between bets)
     while still getting context-aware, tailored axes instead of a blind
     generic grid, and keeps the main session's context clean rather than
     filling it with 5–10 full essay bundles. Default variant count is
     5–10 (see §4).
  Feeds Stage 11.
- **Convergence mode** — produces a single refined draft bundle directly
  in the main conversation, incorporating the prior round's direction and
  retained phrases collaboratively with Jeremy rather than as a blind
  instruction handed to a subprocess. No fork needed — there's exactly one
  variant, and it's meant to be directly collaborative. No tournament;
  Stage 11 is skipped entirely for that round.

**Judge diversity is unaffected by this move.** Stage 11 still requires at
least one judge on a different model than the generator, to reduce
self-preference bias — "the generator" is simply whichever model actually
ran the forks/session that produced the drafts, recorded per-variant in
`vXX.meta.json` exactly as before.

---

### Stage 11 — Judge Panel Evaluation

**Only runs in exploration-mode rounds. The only stage that must stay a
separate, scripted Anthropic API call** (`python scripts/run_judges.py
--gen N`) — see §1. Judges must never share context with the agent/session
that produced the drafts and CV they're evaluating; that isolation is the
entire point of this stage, not an artifact of how it happens to be
implemented.

**Structured rubric, scored per-JD-component and per-question, not free
text — and evaluated as a whole application package, not siloed per
question.** Each judge produces **one evaluation per variant** (not one
per question), covering the full bundle (all question drafts + the
tailored CV): a score and comment for every JD component, a score and
comment for every form question, an evaluation of the CV, a low-weight
style-fidelity check kept separate from content scoring, and an overall
score, outcome, and comment for the whole package. (Exact file shape:
[`data_schemas.md`](data_schemas.md#judge-record).) Written to
`output/evals/genN/vXX_<judge>.json`.

`component_scores` stays **granular** (per individual JD-component id, not
just per section) — this is still what drives Stage 14's decision about
which components need work; the section-level view (required/preferred/
responsibilities/mission) is a Stage 12 rollup for readability, not how
judges score directly. `cv_evaluation` scores the same `cv_tailored.md` for
every variant in a round, since the CV isn't varied per-variant — minor
duplication across judge calls, acceptable as-is. `style_fidelity` stays
structurally separate from content scores, exactly as in the original
design, so it never gets blended into the content-quality ranking.

**Judge diversity, not judge replication.** Run 3–5 judges per variant, not
clones of one persona: vary the judge system-prompt persona, and use a
different model than the generator for at least one judge to reduce
self-preference bias. (An earlier version of this design also called for
varying temperature across judges — dropped, since the Messages API has no
temperature/sampling-randomness parameter to vary; persona and model are
the actual diversity levers now.)

---

### Stage 12 — Aggregation

The agent reads all `output/evals/genN/*.json` directly and produces:

- **`output/evals/genN/summary.json`** — mean/variance of each component
  score per variant (granular, per-component), **plus a section-level
  rollup** (grouped by `required_qualifications` /
  `preferred_qualifications` / `core_responsibilities` /
  `mission_signals`) for a quick read, plus per-question score rollups and
  CV-evaluation consensus. The numeric rollup is arithmetic across many
  judges × variants × components — exactly the kind of thing worth doing
  in actual code rather than eyeballed, so `scripts/aggregate.py` (a plain
  deterministic script, no Anthropic API call, no key required) computes
  it; the agent runs it and reads the result.
- **`output/evals/genN/summary.md`** — human-readable: top 2–3 variants by
  aggregate score, **plus the qualitative comments that recur across ≥2
  judges** — the numeric score tells you *that* something's wrong, the
  recurring comment tells you *what*. This synthesis is done by the agent
  directly, reading the judges' actual comments in context — no separate
  LLM call needed, since the agent doing the synthesis already is one.

Same structure as the manual 9-eval synthesis this whole pipeline
automates: not just counting outcomes, but reading across all judges and
pulling out what repeats.

---

### Stage 13 — Human Sniff Check + Direction Capture

Manual, not scripted — and now simply the point in an ongoing conversation
where the agent stops generating and Jeremy reads. Jeremy reads the top
2–3 variants and `summary.md` himself before anything regenerates — the
ground-truth check a synthetic judge panel can't do on its own (e.g. the
calibration/validation overclaim that no eval agent flagged unprompted,
earlier in the manual process).

**Expanded from the original design:** this checkpoint now also produces
`output/rounds/genN/direction.md` — freeform commentary, plus explicitly
retained phrases or points (from Jeremy's own original response or from
any variation), plus his explicit choice of mode for the next round:

```markdown
---
next_mode: convergence
next_variant_count: null
---
Keep the "belief, not a credential" opening from v07. Cut the
political-fragility paragraph entirely next round — it's the recurring
low-value comment across judges. Retain "no formal validation pipeline"
framing exactly as-is, this is load-bearing for the overclaim correction.
```

---

### Stage 14 — Directed Iteration

**Not a fully automatic genetic/mutation loop.** The agent reads
`output/rounds/genN/direction.md` + `output/evals/genN/summary.md` +
`input/preferences.md` directly and produces
`output/rounds/gen(N+1)/round_config.json` — recording the finalized mode
and variant count for the next round, a pointer back to the direction file
it was built from, and explicit lists of phrases to retain verbatim or
drop. (Exact file shape: [`data_schemas.md`](data_schemas.md#round_configjson).)

Jeremy approves or adjusts before the next generation runs, in the same
conversation. Automatic mutation without a human step is a reasonable
future feature once the rubric and judge panel have proven reliable — not
needed to get value out of v1.

---

## 3. Repo structure

Stays single-application/flat for now — no `applications/<slug>/`
multi-application scaffolding yet. Revisit once a second real application
shows what actually needs to be shared vs. per-application.

```
repo/
├── input/                        # gitignored — human-provided material
│   ├── job_posting.md            # required — pasted verbatim by Jeremy
│   ├── cv/                       # required — one or more CV versions, any format/filename
│   ├── essay/                    # required — one or more free-written content files
│   ├── preferences.md            # optional — how to weight things, human-authored
│   ├── external_resources.md     # optional — list of URLs, one per line
│   ├── external_refs/            # optional — raw files (PDFs etc.)
│   ├── interview_transcripts/    # optional — transcripts/notes from any live interview session
│   └── past_drafts/              # optional — corrected writing samples for voice profiling only
├── output/                       # gitignored — everything the pipeline generates
│   ├── jd_itemised.md
│   ├── jd_components.json
│   ├── form_itemised.md
│   ├── form_questions.json
│   ├── external_references.md
│   ├── tagged_context.json
│   ├── tagged_context.md         # rendered for review only
│   ├── interview_brief.md
│   ├── interview_report.md
│   ├── voice_profile.md
│   ├── cv_tailored.md
│   ├── cv_tailoring_notes.json
│   ├── drafts/
│   │   ├── gen1/
│   │   │   ├── v01/
│   │   │   │   ├── q_why_anthropic.md
│   │   │   │   └── v01.meta.json
│   │   │   └── ...
│   │   └── gen2/
│   ├── evals/
│   │   ├── gen1/
│   │   │   ├── v01_judge_skeptical.json
│   │   │   ├── v01_judge_warm.json
│   │   │   ├── summary.json
│   │   │   └── summary.md
│   │   └── gen2/
│   └── rounds/
│       ├── gen1/
│       │   └── direction.md
│       └── gen2/
│           └── round_config.json
├── scripts/                      # committed — active pipeline code, plus an archive
│   ├── _common.py                # Anthropic SDK helper, used by run_judges.py
│   ├── run_judges.py             # Stage 11: the only stage that must call the Anthropic API
│   ├── aggregate.py              # Stage 12: deterministic numeric rollup, no API key needed
│   └── deprecated/               # not a pipeline stage -- superseded per-stage scripts from
│                                  # before this redesign, kept for reference only
├── .claude/skills/run-cycle/     # committed — the /run-cycle skill (see CLAUDE.md), the
│   └── SKILL.md                  # guided end-to-end way to run this pipeline
├── README.md                     # committed
└── .gitignore
```

**Every stage not listed above** (1, 2, 4, 5, 6's brief/ingest halves, 8,
9, 10, 13, 14) **is performed by the Claude Code agent directly**, per §2 —
there's no separate script to maintain for them, and none is needed: the
output file shapes in [`data_schemas.md`](data_schemas.md) are the
contract, not the mechanism that produced them.

**Only code and documentation are public here.** `input/` and `output/`
are both gitignored, full stop — not just the human-provided raw
material. An earlier version of this design drew the line at "raw input
is private, generated artifact is public," on the reasoning that
generated files like `jd_components.json` just reproduce public posting
text. That missed that most of what actually gets generated — draft essay
text, judge scores and critiques, the tailored CV — *is* the application's
substance and strategy, not just a repackaging of public information, and
shouldn't be sitting in a public repo regardless of whether any single
field in it counts as "personal data." See README.md ("Background") for
why this project is public at all, given that constraint.

`preferences.md` lives in `input/`, not `output/`, despite being a named
pipeline "stage" (Stage 7) — it's human-authored, like the material in
`input/essay/`, not agent-generated.

The `genN` structure under `output/` is still diffable across generations
even though none of it is committed — `git diff --no-index
output/drafts/gen1/v01/q_why_anthropic.md
output/drafts/gen2/v01/q_why_anthropic.md` works fine on untracked files
and watches the essay evolve; `output/evals/genN/summary.md` across
generations gives the same audit trail `git log` would, just read by hand
instead.

---

## 4. Variant count and round mode

Default **5–10 variants** for an exploration-mode round (down from the
original design's 12–16) — narrower on purpose, per Jeremy's stated goal
of spending less time agonizing over the text rather than maximizing
exploration breadth. Each round is explicitly either exploration
(variant tournament + judge panel) or convergence (single refined draft,
no panel) — chosen by Jeremy at Stage 13, not defaulted.

The axes that separate variants within an exploration round are chosen
live, per round, by the agent and Jeremy together (§ Stage 10) — grounded
in what's actually distinctive about the material at hand for that
specific round, not drawn from a fixed generic list. Each variant is then
drafted by its own forked subagent so the axes stay genuinely independent
bets rather than converging mid-session.

Widen exploration only if a round's `summary.md` shows genuinely close
scores across many variants (meaning the axes picked aren't very
discriminating) — that's the signal to add more axes or variants, not a
default starting assumption.

---

## 5. Notes carried over, worth encoding directly into the repo

- A real overclaim made it through several manual drafting rounds during
  the original pilot before being caught — a claim of more direct/solo
  ownership over a piece of collaborative work than was accurate (see
  README "Background" for the actual story; deliberately not repeated
  here, since this document describes general pipeline behavior, not one
  application's specific content). That near-miss is why `overclaim_risk`
  is a permanent, shared-rubric score across both the essay (judge-scored)
  and the CV (`claims_checklist`, Stage 9), not a one-off note — the
  underlying failure mode (drafts drifting toward overstating ownership
  under iterative refinement) is general and likely to recur for any
  application, not specific to one project. It's also the direct reason
  Stage 11 is the one stage in this whole design that keeps its isolation
  from the rest of the session (§1) — the near-miss was caught by
  independence, not by care, and care alone already failed once.
- Keep `overclaim_risk` and a role/mission-specificity score as permanent
  cross-cutting judge scores regardless of which JD this pipeline is later
  pointed at — both were the highest-value findings from the original
  pilot and are likely to generalize beyond any one role.
- Build `output/voice_profile.md` (Stage 8) only from corrected source
  text — proofread drafts and any additional writing samples Jeremy
  supplies, never raw dictated/transcribed originals. Several fixes
  applied earlier in the manual process (subject-verb agreement, dropped
  words, broken parallelism) were transcription artifacts, not style, and
  should not be encoded into the profile as if they were. **Resolved:**
  `output/interview_report.md`'s verbatim quotes (Stage 6) get no
  exemption from this rule — they're still fair game for direct reuse in
  drafting (Stage 10), but need the same light grammar pass as any other
  sample before feeding Stage 8. Compelling content and clean prose are
  different axes; one doesn't imply the other.
- Treat style-matching as a one-time distillation applied at generation
  time, not an iterative optimization target — an iterative "regenerate
  until style score is high" loop tends to converge toward near-verbatim
  reuse of source phrasing, defeating the purpose of producing genuine
  variations. `style_fidelity` exists only to catch drift toward generic
  AI-assistant phrasing, and triggers a single targeted regeneration,
  never a full re-optimization pass.
- The itemize/human-verify pattern (Stages 1–2) exists because fidelity to
  source matters everywhere in this pipeline, not just for overclaim risk
  about Jeremy's own experience: a JD or form that's been silently
  compressed or trimmed during itemization poisons every score that traces
  back to it, the same way a bad `jd_components.json` would. An earlier
  version of this design also had a script/agent fetch the posting by URL
  and cross-check the itemization with a second automated call — cut in
  favor of a direct human paste (removes the fetch-fidelity risk entirely)
  plus a live human check against material he already has open (at least
  as reliable as a second agent call, and now a real-time conversation
  rather than a rerun-and-reread cycle). The first real run of this stage
  (against a live JD posting) caught genuine omissions this way — a
  dropped location line, a few ellipsis-truncated clauses — so the
  checkpoint itself is worth keeping even though the original
  fetch/agent-verify mechanism around it wasn't, and even though the
  itemizing mechanism has since changed again (script → in-context agent).
- **The naivety/context split (§1) is the organizing principle for
  execution, not an incidental implementation choice.** When adding a new
  stage or reconsidering an existing one, the question to ask is not "does
  this need an LLM call" (almost everything here does) but "does this
  stage's value depend on the executor not having been part of the
  conversation that produced what it's working on." Only Stage 11 answers
  yes. Stage 10 looked like a plausible second answer at first pass
  (variant diversity), but the actual requirement there is independence
  *between variants*, not independence from the session — which is why
  forked subagents solve it without needing to route generation back
  through the Anthropic API.
