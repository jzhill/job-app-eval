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

## `tagged_context.json`

Produced by Stage 5.

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

Produced by Stage 9.

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

`overclaim_risk` uses the same 1–5 scale as the judge record's
`overclaim_risk`-equivalent scoring, for one consistent audit trail across
the essay and CV paths.

---

## Judge record

Produced by Stage 11. One file per (variant, judge):
`evals/genN/vXX_<judge>.json`.

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

Produced by Stage 14.

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
