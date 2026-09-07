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
5 = <what fully meeting a component/question looks like>
...
1 = <what no evidence, or contradicting evidence, looks like>

## Id usage
Use component/question ids exactly as given in jd_components.json /
form_questions.json. Never rename, invent, or duplicate a key.

## overall_score -> overall_outcome rule
<the stated threshold/logic, agreed live with Jeremy>

## Comment length
- Component/question/CV/style_fidelity comments: <= 40 words each.
- overall_candidate_feedback: <= 100 words.
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

`component_scores` keys are JD-component ids from `jd_components.json`;
`question_scores` keys are question ids from `form_questions.json`.

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

`mode` is one of `exploration` or `convergence` (see design doc §4).
