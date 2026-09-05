# Design: Agentic Job-Application Drafting & Evaluation Pipeline

A small Python repo, built with Claude Code, that automates a manual workflow
prototyped by hand in a claude browser session. High level process: JD- and
form-referenced draft generation, informed by a one-time distilled voice
profile and a reflective interview, → structured multi-judge evaluation of
the whole application package → aggregated feedback → human-directed
iteration.

This is v1 of a design meant to generalize beyond a single application
(originally Anthropic's Partner Manager, Global Health role). The repo
itself stays single-application/flat for now (see §3) — the generalization
is in the pipeline's shape, not yet in the folder structure.

---

## 1. Core principle

**Everything is scored against the job description, not against a generic
rubric.** The JD is decomposed once, up front, into labeled components.
Every downstream score — quantitative and qualitative — is tied back to one
or more of those components. This is what turns "does this sound good" into
"does this answer what the employer actually asked for."

The human (Jeremy) stays in the loop at three points by design, not as a
fallback:
1. after context mapping, approving the machine's tagging of his own raw
   material against JD components (§ Stage 5) — a harder review than
   approving his own writing, since he's now checking someone else's
   interpretation of his words, not his own;
2. as an active participant in the reflective interview itself (§ Stage 6),
   not a passive input source;
3. after each evaluation round, doing the "sniff test" on top candidates and
   supplying direction before the next generation runs (§ Stage 13).

The pipeline drafts and scores; it does not decide alone.

---

## 2. Pipeline stages

```
1.  JD Decomposition            → jd_raw.md → jd_itemised.md → jd_components.json
2.  Form Decomposition          → form_raw.md → form_itemised.md → form_questions.json
3.  Raw Context Capture         → raw_context.md
4.  External Reference Ingestion → external_references.md
5.  Context Mapping             → tagged_context.json (+ tagged_context.md)
6.  Reflective Interview        → interview_report.md
7.  Preferences File            → preferences.md
8.  Voice Profiling             → voice_profile.md
9.  CV Tailoring                → cv_tailored.md + cv_tailoring_notes.json
10. Draft Generation            → drafts/genN/vXX/q<question_id>.md + vXX.meta.json
11. Judge Panel Evaluation      → evals/genN/vXX_<judge>.json
12. Aggregation                 → evals/genN/summary.json + summary.md
13. Human Sniff Check           → rounds/genN/direction.md (manual, not scripted)
14. Directed Iteration          → rounds/gen(N+1)/round_config.json
```

Each stage is a separate script/module, callable independently, so you can
re-run stage 11 alone if you tweak the judge panel without regenerating
drafts.

---

### Stage 1 — JD Decomposition

**Input:** a URL to the job posting (job board link) or pasted raw text.

**Step 1a — Verbatim capture.** Fetch (if URL) or accept (if pasted) the JD
text and capture it exactly as presented — preserving headings and bullet
structure, no paraphrasing or summarizing. Output: `jd_raw.md`.

**Step 1b — Itemization.** Break `jd_raw.md` into a discrete, numbered list
of items — every distinct requirement, responsibility, sentence, or bullet
gets its own item, grouped under whatever section headers the source page
itself used. This is a structural pass only; it is not yet the four-category
semantic pass below. Output: `jd_itemised.md`.

**Step 1c — Verification.** An automated cross-check — ideally a fresh
call/context, not the same one that produced the itemised file, mirroring
the judge panel's own diversity principle (§ Stage 11) — compares
`jd_itemised.md` against `jd_raw.md` item by item to confirm nothing was
dropped, paraphrased, or invented. This guards against a real,
generalizable risk: an LLM asked to "parse" a posting can quietly summarize
or omit a bullet, and since every downstream score in this pipeline traces
back to `jd_components.json`, an unfaithful source poisons everything
after it. A discrepancy triggers re-itemization, not silent correction.

**Step 1d — Semantic decomposition.** The verified `jd_itemised.md` — not
the raw scrape directly — is decomposed into `jd_components.json`:

```json
{
  "required_qualifications": [
    {"id": "req_clinical_ai", "text": "Direct experience evaluating/validating clinical AI or ML tools"}
  ],
  "preferred_qualifications": [
    {"id": "pref_llm_specific", "text": "Hands-on AI/ML product experience (eval harnesses, guardrails)"}
  ],
  "core_responsibilities": [
    {"id": "resp_partnerships", "text": "Build research partnerships with governments and institutions"}
  ],
  "mission_signals": [
    {"id": "mission_reliable_ai", "text": "Reliable, interpretable, steerable AI"}
  ]
}
```

**Reviewed and hand-edited by Jeremy** — a wrong or sloppy decomposition
poisons every downstream score. These four top-level keys
(`required_qualifications`, `preferred_qualifications`,
`core_responsibilities`, `mission_signals`) are also the grouping used for
the section-level rollup in Stage 12 (Aggregation).

---

### Stage 2 — Form Decomposition

**Input:** a URL to the actual application form (the employer's application
portal — a different document from the JD posting; for the Anthropic
application in progress, the JD is confirmed but the form's actual question
count is not) or pasted raw text.

**Step 2a — Verbatim capture** → `form_raw.md`, same fidelity rule as
Stage 1a.

**Step 2b — Itemization** → `form_itemised.md` — every field/question
captured as its own item, with whatever prompt text and stated limit
appear on the source page.

**Step 2c — Verification** → the same fresh-context cross-check as Stage
1c, confirming nothing was dropped or altered before proceeding.

**Step 2d — Structural decomposition** → `form_questions.json`, purely
structural facts about the form itself. Deliberately does **not**
pre-assign JD components to a question; that mapping happens at generation
time (Stage 10), not here.

```json
{
  "questions": [
    {"id": "q_why_anthropic", "prompt_text": "Why do you want to work at Anthropic?",
     "limit": {"type": "words", "max": 400}, "required": true}
  ]
}
```

A generated draft references its question by file location, not an
embedded field: `drafts/genN/vXX/q_why_anthropic.md`. This keeps the
reference unambiguous and lets Stages 11–12 glob by question id.

---

### Stage 3 — Raw Context Capture

**Input:** Jeremy, writing freely.

**Output:** `raw_context.md` — fully unstructured prose. No required
headers, no `[addresses: ...]` tagging. He should write toward the JD
loosely — attending to it, but without forcing himself into per-component
or per-question structure, jumping between experience, motivation, and
reflection in whatever order it comes out. The mapping work belongs to
Stage 5, not to him.

---

### Stage 4 — External Reference Ingestion

**Input:** a list of resources Jeremy has collected as relevant background
— URLs (articles, org pages, reports) and/or files (PDFs etc.). This is
material about the external world, not personal experience.

**Process:** each resource gets a quick, single-pass parse — lightweight,
not the multi-step verbatim/verify treatment JD/form intake gets (§ Stages
1–2), since this is supplementary grounding material, not a structural
document everything else traces back to. Capture: the source (URL or
filename), a concise summary of its key content, and an optional short note
from Jeremy on why he flagged it. Even without an explicit note, the fact
Jeremy selected a given resource is itself signal about what he finds
relevant or compelling.

**Output:** `external_references.md` — one entry per resource:

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

**Input:** `raw_context.md`, `external_references.md`, `jd_components.json`,
`form_questions.json`.

**Output:** `tagged_context.json` — the canonical, machine-generated
mapping of fragments onto JD components and (once available) form
questions, with a confidence field per fragment and an `origin` field
distinguishing personal material from external reference material. A
`tagged_context.md` rendering (grouped by JD component, in the same visual
shape the original hand-tagged file used) is auto-generated purely for the
human checkpoint — Jeremy never edits it directly; he approves it or kicks
back specific fragments for correction.

```json
{
  "fragments": [
    {"id": "frag_003", "source_excerpt": "In Kiribati, after landscaping commercial AI X-ray systems...",
     "jd_component_ids": ["req_clinical_ai", "resp_theory_of_change"],
     "form_question_ids": ["q_why_anthropic"], "confidence": "high",
     "origin": "raw_context"},
    {"id": "frag_012", "source_excerpt": "Beneficial Deployments' Gates Foundation partnership...",
     "jd_component_ids": ["mission_beneficial_deployments"],
     "form_question_ids": [], "confidence": "high",
     "origin": "external_reference"}
  ],
  "coverage_gaps": [
    {"jd_component_id": "resp_partnerships", "status": "weak"}
  ]
}
```

**`origin` matters beyond bookkeeping:** CV Tailoring's `claims_checklist`
(Stage 9) may only trace a claim about Jeremy's own experience to a
`raw_context` (or interview-derived) fragment — never to an
`external_reference` fragment, since a claim about Jeremy cannot be
supported by something he merely read.

**This checkpoint is harder than the original design's version.** Jeremy is
no longer approving his own tagging — he's approving an LLM's
interpretation of his own words. `tag_context.py` should flag low-confidence
mappings for priority review so this checkpoint doesn't get rubber-stamped.
`coverage_gaps` is computed here but does not gate Stage 6 — it's
informational input to it, not a precondition.

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
relevant, non-generic questions — the JD, `jd_components.json`,
`tagged_context.json` (including coverage gaps and external-reference
fragments, as hints toward under-explored territory, not a script to
follow), and the CV.

**Output:** `interview_report.md` — an organized, annotated write-up of the
exchange (not a raw transcript), with a clearly separated section of
verbatim quotes or passages flagged as particularly compelling — candidates
for direct, unaltered reuse in later drafts. This feeds forward as its own
first-class input to Stage 10, distinct from `tagged_context.json` — it is
not merged back into the tagged-context file.

**Open note:** whether these verbatim quotes count as "corrected" text for
Stage 8's sourcing rule, or need a light grammar pass first (they may
originate from live dialogue the same way flagged transcription artifacts
did in the original process) — decide before this stage is implemented.

**Delivery mechanism: this interview does not run inside Claude Code.**
Claude Code has no voice interface, and there is no session handoff between
Claude Code and claude.ai/Gemini/ChatGPT's voice-mode apps — they don't
share context, the same way claude.ai's memory doesn't carry into Claude
Code (see project history). The best setting for this interview is
conversational and hands-free (driving, walking), which points squarely at
an external voice-mode app, not this tool. So `interview.py` does not
conduct the conversation itself. It has two jobs:

1. **Generate a portable interview brief** — a self-contained prompt
   (since the external session starts with zero context, same reasoning as
   the original handover doc) bundling the JD, the relevant
   `jd_components.json` entries, `tagged_context.json`'s coverage gaps, CV
   highlights, and explicit instructions on interview style (curious,
   thoughtful, not rote Q&A) and the exact output shape wanted back
   (organized report + a separated verbatim-quotes section). Jeremy copies
   this into Claude/Gemini/ChatGPT's voice mode and has the actual
   conversation there.
2. **Ingest the pasted-back result** into `interview_report.md`, normalizing
   whatever shape the external agent returned into the schema above.

---

### Stage 7 — Preferences File

Unchanged in spirit from the original design: not *facts about Jeremy*, but
*how he wants the pipeline to weight things*. Kept distinct from context so
it's easy to update without touching the factual record, and kept
**durable across rounds** — per-round tactical notes belong in
`rounds/genN/direction.md` (Stage 13), not here, so this file doesn't
accumulate noise round over round or application over application.

```markdown
# Preferences

- Prioritize the evaluation-philosophy argument (context-adaptive validation)
  as the intellectual centerpiece — it is the strongest, most original idea.
- Do not overclaim sole ownership of collaborative work. Frame the Kiribati
  AI work as close vendor collaboration + implementation/capability
  evaluation, not formal model validation — this is factually accurate and
  should never be reverted.
- Voice: plain, declarative sentences. Avoid stacking more than one
  "big idea" in a closing paragraph.
```

---

### Stage 8 — Voice Profiling

Unchanged from the original design. A single analysis LLM call (not a
loop) over corrected source text only — proofread past drafts and any
additional writing samples, **never** raw dictated/transcribed originals,
since transcription artifacts (subject-verb agreement, dropped words,
broken parallelism) risk being encoded as "voice" if the profiling pass
runs on unfiltered text. Output: `voice_profile.md`, a fixed input to every
Stage 10 generation call, not regenerated per variant or per round.

**Guardrail for the judge panel:** a distinct, low-weight `style_fidelity`
check (see Stage 11), separate from content-quality scores, catches drift
toward generic "assistant voice." A failing variant gets a single targeted
regeneration — never a full re-optimization pass. Style-matching is a
one-time distillation applied at generation time, not an iterative
optimization target: an iterative "regenerate until style score is high"
loop tends to converge toward near-verbatim reuse of source phrasing, which
defeats the purpose of producing genuine variations.

---

### Stage 9 — CV Tailoring

**New stage** — the CV was previously static input context only.

**Input:** `jd_components.json`, `tagged_context.json`, the current CV,
`preferences.md`.

**Output:** `cv_tailored.md` (reordered/re-emphasized bullets and summary,
same section structure as the source CV) and `cv_tailoring_notes.json` —
the auditable rationale plus a `claims_checklist` that traces every claim
back to a specific context fragment (`origin: raw_context` or an
interview-derived fragment only — never `origin: external_reference`, per
Stage 5) or flags it as unsupported:

```json
{
  "changes": [
    {"section": "PEARL entry", "change": "moved AI X-ray bullet to lead position",
     "reason": "matches req_clinical_ai, previously buried"}
  ],
  "claims_checklist": [
    {"claim": "worked closely with Delft and Fuji to select and adopt AI X-ray tools",
     "traceable_to": "frag_003", "overclaim_risk": {"score": 1, "comment": "supported, matches corrected framing"}},
    {"claim": "calibrated detection thresholds", "traceable_to": null,
     "overclaim_risk": {"score": 5, "comment": "matches known prior overclaim pattern — do not include"}}
  ]
}
```

**Deliberately single-pass, not a variant tournament.** CVs are
factual/structured and lower voice-sensitivity than an essay, so the
overclaim risk (a real, hard-won lesson — see §5) is better guarded
directly via this checklist than explored stylistically via multiple
generations. `overclaim_risk` here uses **the same 1–5 scale** as the
essay's judge-scored `overclaim_risk` (Stage 11), for one consistent
audit trail across both artifacts.

---

### Stage 10 — Draft Generation

**Input:** `jd_components.json`, `tagged_context.json`,
`interview_report.md`, `external_references.md`, `form_questions.json`,
`preferences.md`, `voice_profile.md`, and the current round's
`rounds/genN/round_config.json` (mode + variant count + carried-forward
direction from the prior round, if any — see Stage 14).

**Output:** `drafts/genN/vXX/q<question_id>.md` per question, plus
`vXX.meta.json` recording the axis combination that produced it.

**Generalized from one essay to N questions.** `form_questions.json` may
list one question or several; each variant is one coherent bundle of
answers across *all* questions, generated together in a single call so
answers don't repeat or collide with each other.

**Mode-aware**, per `round_config.json`:
- **Exploration mode** — produces the full variant set (default 5–10
  variants, down from the original design's 12–16, per Jeremy's stated
  goal of reducing his own time agonizing over text). Feeds Stage 11.
- **Convergence mode** — produces a single refined draft bundle directly,
  incorporating the prior round's direction and retained phrases. No
  tournament; Stage 11 is skipped entirely for that round.

Use the Anthropic API directly for this (not Claude Code's own agentic
loop) so each call is a clean, scriptable, loggable unit.

---

### Stage 11 — Judge Panel Evaluation

**Only runs in exploration-mode rounds.**

**Structured rubric, scored per-JD-component and per-question, not free
text — and evaluated as a whole application package, not siloed per
question.** Each judge produces **one record per variant** (not one per
question), covering the full bundle (all question drafts + the tailored
CV):

```json
{
  "variant_id": "gen3_v07",
  "judge_id": "judge_skeptical_senior",
  "component_scores": {
    "req_clinical_ai": {"score": 4, "comment": "Concrete Kiribati example, but doesn't name what was non-standard vs off-the-shelf CAD4TB."},
    "resp_partnerships": {"score": 2, "comment": "Almost entirely absent."}
  },
  "question_scores": {
    "q_why_anthropic": {"score": 4, "comment": "Strong, direct answer to the actual prompt."}
  },
  "cv_evaluation": {"score": 4, "comment": "AI X-ray work now visible and quantified; good."},
  "style_fidelity": {"score": 4, "comment": "One sentence drifts toward generic phrasing mid-paragraph 3.",
                      "weight": "low — sanity check only, not blended into content scores"},
  "overall_score": 4,
  "overall_outcome": "screen_in",
  "overall_candidate_feedback": "Strong on validation philosophy, weak on partnership evidence."
}
```

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
clones of one persona: vary the judge system-prompt persona, vary
temperature across judges, and use a different model than the generator
for at least one judge to reduce self-preference bias.

---

### Stage 12 — Aggregation

`aggregate.py` reads all `evals/genN/*.json`, produces:

- **`summary.json`** — mean/variance of each component score per variant
  (granular, per-component), **plus a section-level rollup** (grouped by
  `required_qualifications` / `preferred_qualifications` /
  `core_responsibilities` / `mission_signals`) for a quick read, plus
  per-question score rollups and CV-evaluation consensus.
- **`summary.md`** — human-readable: top 2–3 variants by aggregate score,
  **plus the qualitative comments that recur across ≥2 judges** — the
  numeric score tells you *that* something's wrong, the recurring comment
  tells you *what*.

Same structure as the manual 9-eval synthesis this whole pipeline
automates: not just counting outcomes, but reading across all judges and
pulling out what repeats.

---

### Stage 13 — Human Sniff Check + Direction Capture

Manual, not scripted. Jeremy reads the top 2–3 variants and `summary.md`
himself before anything regenerates — the ground-truth check a synthetic
judge panel can't do on its own (e.g. the calibration/validation overclaim
that no eval agent flagged unprompted, earlier in the manual process).

**Expanded from the original design:** this checkpoint now also produces
`rounds/genN/direction.md` — freeform commentary, plus explicitly retained
phrases or points (from Jeremy's own original response or from any
variation), plus his explicit choice of mode for the next round:

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

**Not a fully automatic genetic/mutation loop.** The orchestrator reads
`rounds/genN/direction.md` + `summary.md` + `preferences.md` and produces
`rounds/gen(N+1)/round_config.json` — finalizing mode and variant count
explicitly for the next round rather than defaulting:

```json
{
  "mode": "convergence",
  "variant_count": 1,
  "carried_forward_commentary": "rounds/genN/direction.md",
  "retain_verbatim": ["belief, not a credential opening (v07)"],
  "drop": ["political-fragility paragraph"]
}
```

Jeremy approves or adjusts before the next generation runs. Automatic
mutation without a human step is a reasonable future feature once the
rubric and judge panel have proven reliable — not needed to get value out
of v1.

---

## 3. Repo structure

Stays single-application/flat for now — no `applications/<slug>/`
multi-application scaffolding yet. Revisit once a second real application
shows what actually needs to be shared vs. per-application.

```
repo/
├── input/                       # gitignored — raw personal source material
│   ├── cv_source.md
│   ├── external_refs/           # raw files (PDFs etc.) Jeremy collects
│   └── past_drafts/
├── jd_raw.md
├── jd_itemised.md
├── jd_components.json
├── form_raw.md
├── form_itemised.md
├── form_questions.json
├── external_references.md
├── raw_context.md
├── tagged_context.json
├── tagged_context.md            # auto-rendered, for review only
├── interview_report.md
├── preferences.md
├── voice_profile.md
├── cv_tailored.md
├── cv_tailoring_notes.json
├── drafts/
│   ├── gen1/
│   │   ├── v01/
│   │   │   ├── q_why_anthropic.md
│   │   │   └── v01.meta.json
│   │   └── ...
│   └── gen2/
├── evals/
│   ├── gen1/
│   │   ├── v01_judge_skeptical.json
│   │   ├── v01_judge_warm.json
│   │   ├── summary.json
│   │   └── summary.md
│   └── gen2/
├── rounds/
│   ├── gen1/
│   │   └── direction.md
│   └── gen2/
│       └── round_config.json
├── scripts/
│   ├── decompose_jd.py          # Stage 1: capture, itemize, verify, decompose
│   ├── decompose_form.py        # Stage 2: same treatment for the form
│   ├── ingest_references.py     # Stage 4
│   ├── tag_context.py           # Stage 5
│   ├── interview.py             # Stage 6: brief-out / ingest-back, not the conversation itself
│   ├── build_voice_profile.py
│   ├── tailor_cv.py
│   ├── generate_drafts.py
│   ├── run_judges.py
│   ├── aggregate.py
│   └── plan_next_gen.py
└── README.md
```

`jd_raw.md`/`jd_itemised.md`/`form_raw.md`/`form_itemised.md` reproduce
public posting text (not personal information), so — like
`jd_components.json` — they're intended to be public, part of the same
audit trail. Raw files Jeremy collects for Stage 4 (PDFs etc.) live in
`input/external_refs/` and stay gitignored; the `external_references.md`
digest generated from them is public.

Git-trackable and diffable across generations by design — `git diff
drafts/gen1/v01/q_why_anthropic.md drafts/gen2/v01/q_why_anthropic.md`
watches the essay evolve, and `git log evals/` gives an audit trail of how
scores moved.

---

## 4. Variant count and round mode

Default **5–10 variants** for an exploration-mode round (down from the
original design's 12–16) — narrower on purpose, per Jeremy's stated goal
of spending less time agonizing over the text rather than maximizing
exploration breadth. Each round is explicitly either exploration
(variant tournament + judge panel) or convergence (single refined draft,
no panel) — chosen by Jeremy at Stage 13, not defaulted.

Widen exploration only if a round's `summary.md` shows genuinely close
scores across many variants (meaning the axes picked aren't very
discriminating) — that's the signal to add more axes or variants, not a
default starting assumption.

---

## 5. Notes carried over, worth encoding directly into the repo

- The corrected, accurate framing of the Kiribati work (no formal model
  validation/calibration; close vendor collaboration + implementation/
  capability evaluation) is encoded in `preferences.md` as a hard
  constraint, not just a note — this was a real overclaim that made it
  through several manual generations before being caught, and is exactly
  why `overclaim_risk` now uses one shared rubric across both the essay
  (judge-scored) and the CV (`claims_checklist`, Stage 9).
- The single most-praised idea across the manual 9-eval run
  (context-adaptive validation / political-fragility spectrum / data
  sovereignty) maps to a specific `resp_theory_of_change` JD component so
  the pipeline can verify it's preserved across variants, rather than
  trusting it survives by default.
- Keep `overclaim_risk` and a role/mission-specificity score as permanent
  cross-cutting judge scores regardless of which JD this pipeline is later
  pointed at — both were the highest-value findings from the manual
  process and are likely to generalize beyond this one role.
- Build `voice_profile.md` (Stage 8) only from corrected source text —
  proofread drafts and any additional writing samples Jeremy supplies,
  never raw dictated/transcribed originals. Several fixes applied earlier
  in the manual process (subject-verb agreement, dropped words, broken
  parallelism) were transcription artifacts, not style, and should not be
  encoded into the profile as if they were. **Open question:** whether
  `interview_report.md`'s verbatim quotes (Stage 6) count as "corrected"
  for this rule, or need a light grammar pass first — unresolved, decide
  before Stage 8 is implemented against real interview output.
- Treat style-matching as a one-time distillation applied at generation
  time, not an iterative optimization target — an iterative "regenerate
  until style score is high" loop tends to converge toward near-verbatim
  reuse of source phrasing, defeating the purpose of producing genuine
  variations. `style_fidelity` exists only to catch drift toward generic
  AI-assistant phrasing, and triggers a single targeted regeneration,
  never a full re-optimization pass.
- The verbatim-capture/itemize/verify pattern (Stages 1–2) exists because
  fidelity to source matters everywhere in this pipeline, not just for
  overclaim risk about Jeremy's own experience: a JD or form that's been
  silently paraphrased or trimmed during "parsing" poisons every score
  that traces back to it, the same way a bad `jd_components.json` would.
