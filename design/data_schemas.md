# Data schemas

Exact file shapes for the pipeline's generated artifacts, pulled out of
the main design doc so that one stays readable prose and this one stays a
precise reference. Each entry is linked from the stage in
[`agentic_application_eval_design.md`](agentic_application_eval_design.md)
that produces it — read that first for *why* a file looks the way it does;
this doc only says *what* it looks like.

---

## `jd_components.json`

Produced by Stage 1.

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

---

## `form_questions.json`

Produced by Stage 2.

```json
{
  "questions": [
    {"id": "q_why_anthropic", "prompt_text": "Why do you want to work at Anthropic?",
     "limit": {"type": "words", "max": 400}, "required": true}
  ]
}
```

---

## `marking_guide.md`

Produced by Stage 3. Prose, not JSON — a rubric document, not a data
record. Expected sections:

```markdown
# Marking Guide

## Score anchors (1-5)
5 = <what fully meeting a component/question/CV looks like>
...
1 = <what no evidence, or contradicting evidence, looks like>
Applies to required/preferred qualification and core-responsibility
component scores, question scores, and the CV score. `mission_signals`
items are not scored individually -- context only, weighed into the vibe
score and qualitative assessments instead.

## Id usage
Use component ids (required_qualifications/preferred_qualifications/
core_responsibilities only) exactly as given in jd_components.json, and
question ids exactly as given in form_questions.json. Never rename,
invent, or duplicate a key.

## Section assessments
One <=40-word qualitative synopsis per scored section (required_
qualifications, preferred_qualifications, core_responsibilities) --
the pattern across that section's items, not a restatement of the
per-item comments.

## Vibe score -> overall_outcome rule
<the stated 0-100 threshold/logic, agreed live with Jeremy -- vibe_score
is the judge's independent holistic score, not a computed average>

## Comment length
- Component/question/CV comments and section assessments: <= 40 words each.
- overall_assessment / candidate_feedback: <= 100 words each.
(Starting default -- adjust live with Jeremy if a real run shows it's too
tight or too loose.)
```

Read directly by `scripts/run_judges.py`, which splices its contents into
the judge system prompt — see design doc Stage 3/Stage 13.

---

## `drafting_guide.md`

Produced by Stage 4. Prose, not JSON. Expected sections:

```markdown
# Drafting Guide

## Per-question content boundaries
q_why_anthropic: <what this question is for, what it should NOT cover>
q_ai_fluency: <...>
...

## Whole-variant cohesion requirement
<the standing rule that all answers + the CV must read as one coordinated
application with consistent claims>

## Consistency check (replaces a separate overclaim score)
<the standing instruction that claims about Jeremy's own experience must
not exceed what cv_tailored.md / tagged_context.json actually support>
```

Read by every Stage 12 forked variant subagent, alongside
`voice_profile.md` — see design doc Stage 4/Stage 12.

---

## `output/drafts/genN/<variant_id>.md`

Produced by Stage 12. One file per variant — every question's answer in
one document, each under a heading tagged with its question id so
`scripts/run_judges.py` can split it back into a `{question_id: text}`
map deterministically (not left to the judge to infer). No per-variant
folder — the `.md` and its `.meta.json` sidecar (below) sit directly in
`output/drafts/genN/`, since a variant is now exactly those two files:

```markdown
## [q_why_anthropic] Why do you want to work at Anthropic?

<answer text>

## [q_ai_fluency] Describe your AI fluency

<answer text>
```

Heading format is exactly `## [<question_id>] <anything>` — the bracketed
id is what's parsed; the rest is free text for readability. One heading
per id in `form_questions.json`, no more, no fewer — `run_judges.py`
raises if the set of ids found doesn't match exactly, same as the
existing `question_scores`/`component_scores` key validation.

---

## `output/drafts/genN/<variant_id>.meta.json`

Produced by Stage 12, alongside `<variant_id>.md`. `variant_id` is the
shared filename stem — an opaque string, not required to follow a `vNN`
pattern (a comparison round might use lineage-carrying ids like
`r3v1-jh`).

```json
{
  "variant_id": "v01",
  "mode": "convergence",
  "rationale": "Directed convergence draft per output/rounds/gen2/direction.md...",
  "model": "claude-sonnet-5",
  "questions_answered": ["q_ai_fluency", "q_low_resource_experience", "q_why_anthropic", "q_cover_letter_additional"]
}
```

Comparison-mode variants (§4 of the design doc) add two fields describing
how the variant came to exist, since it wasn't drafted fresh:

```json
{
  "variant_id": "r3v1-jh",
  "mode": "comparison",
  "production_method": "Jeremy's own hand edit",
  "derived_from": "gen3/v01",
  "rationale": "Trimmed the repeated colleagues/admiration passage, tightened q_why_anthropic's closing paragraph.",
  "questions_answered": ["q_ai_fluency", "q_low_resource_experience", "q_why_anthropic", "q_cover_letter_additional"]
}
```

`production_method` is one of: `"unmodified copy"`, `"Jeremy's own hand
edit"`, `"external tool"` (name the tool), or `"freshly generated"` (the
normal case for exploration/convergence — `derived_from` is omitted then).

---

## `tagged_context.json`

Produced by Stage 7.

```json
{
  "fragments": [
    {"id": "frag_003", "source_excerpt": "In Kiribati, after landscaping commercial AI X-ray systems...",
     "jd_component_ids": ["req_clinical_ai", "resp_theory_of_change"],
     "form_question_ids": ["q_why_anthropic"], "confidence": "high",
     "origin": "essay_response"},
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

`origin` is one of `essay_response`, `interview`, or `external_reference`.

---

## `cv_tailoring_notes.json`

Produced by Stage 11.

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

`overclaim_risk` is scored only here (Stage 11) — the essay side of the
same concern is a plain drafting-time consistency instruction in
`drafting_guide.md` (Stage 4), not a parallel scored field in the judge
record.

---

## Judge record

Produced by Stage 13. One file per (variant, judge):
`output/evals/genN/vXX_<judge>.json`.

```json
{
  "variant_id": "gen3_v07",
  "judge_id": "judge_skeptical_senior",
  "component_scores": {
    "req_clinical_ai": {"score": 4, "comment": "Concrete Kiribati example, but doesn't name what was non-standard vs off-the-shelf CAD4TB."},
    "resp_partnerships": {"score": 2, "comment": "Almost entirely absent."}
  },
  "section_assessments": {
    "required_qualifications": "Clinical/field grounding is strong throughout; AI-validation depth is the weak point.",
    "preferred_qualifications": "Healthtech-company experience is the clear gap; everything else partially present.",
    "core_responsibilities": "Partnership-building evidenced well; regulatory engagement thinner."
  },
  "question_scores": {
    "q_why_anthropic": {"score": 4, "comment": "Strong, direct answer to the actual prompt."}
  },
  "cv_evaluation": {"score": 4, "comment": "AI X-ray work now visible and quantified; good."},
  "vibe_score": 78,
  "overall_outcome": "borderline",
  "overall_assessment": "Strong on validation philosophy and field grounding, weak on partnership evidence and healthtech exposure. Real candidate, not a top screen.",
  "candidate_feedback": "Strong on validation philosophy, weak on partnership evidence."
}
```

`component_scores` keys are JD-component ids from `jd_components.json`
(`required_qualifications`/`preferred_qualifications`/`core_responsibilities`
only -- `mission_signals` items aren't scored individually);
`question_scores` keys are question ids from `form_questions.json`.
`vibe_score` is the judge's independent holistic 0-100 score, not a
computed average of the scores above.

---

## `round_config.json`

Produced by Stage 16.

```json
{
  "mode": "convergence",
  "variant_count": 1,
  "carried_forward_commentary": "rounds/genN/direction.md",
  "retain_verbatim": ["belief, not a credential opening (v07)"],
  "drop": ["political-fragility paragraph"]
}
```

`mode` is one of `exploration`, `convergence`, or `comparison` (see design
doc §4). For a comparison round, `retain_verbatim`/`drop` don't really
apply the same way — describe the intended variant set instead (e.g. which
prior variant to carry forward unmodified, which to hand-edit, which to
run through an external tool, and what direction a freshly-generated
variant should follow).
