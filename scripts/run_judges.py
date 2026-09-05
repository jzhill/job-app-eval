"""Stage 11: Judge Panel Evaluation.

Usage: python scripts/run_judges.py --gen 1

Only runs in exploration-mode rounds -- skipped (with a message) if the
round's config says convergence. Each judge produces one evaluation per
variant covering the whole application package (all question drafts +
the tailored CV), not one evaluation per question.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, call, parse_json, read_json, read_text, write_json

JUDGES = [
    {"id": "judge_skeptical_senior",
     "persona": "You are a skeptical senior reviewer. You've seen hundreds of applications and are quick to spot vague claims, generic phrasing, and unsupported assertions.",
     "temperature": 0.3},
    {"id": "judge_warm_screener",
     "persona": "You are a warm first-read screener. You're looking for genuine enthusiasm and fit, and give candidates the benefit of the doubt on rough edges, while still noting real gaps.",
     "temperature": 0.5},
    {"id": "judge_domain_expert",
     "persona": "You are a technically literate domain expert in this specific field. You test whether the candidate demonstrates real, specific knowledge of the field's landscape, not just generic competence language.",
     "temperature": 0.4},
]

SYSTEM_TEMPLATE = """{persona}

Score this job application (all question answers + the tailored CV) as
one package against the JD components and form questions provided.

Output ONLY a JSON object:
{{"component_scores": {{"<jd_component_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"question_scores": {{"<question_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"cv_evaluation": {{"score": 1-5, "comment": "..."}},
"style_fidelity": {{"score": 1-5, "comment": "...", "weight": "low -- sanity check only, not blended into content scores"}},
"overall_score": 1-5, "overall_outcome": "screen_in"|"screen_out",
"overall_candidate_feedback": "..."}}
Score every JD component and every question given, even briefly."""


def main():
    if "--gen" not in sys.argv:
        raise SystemExit("Usage: python scripts/run_judges.py --gen <N>")
    gen = int(sys.argv[sys.argv.index("--gen") + 1])

    config_path = ROOT / "rounds" / f"gen{gen}" / "round_config.json"
    if config_path.exists() and read_json(config_path)["mode"] == "convergence":
        print(f"gen{gen} is a convergence round -- no judge panel runs.")
        return

    components = read_json(ROOT / "jd_components.json")
    questions = read_json(ROOT / "form_questions.json")
    cv_path = ROOT / "cv_tailored.md"
    cv_text = read_text(cv_path) if cv_path.exists() else "(no tailored CV yet)"

    gen_dir = ROOT / "drafts" / f"gen{gen}"
    variant_dirs = sorted(p for p in gen_dir.iterdir() if p.is_dir())

    evals_dir = ROOT / "evals" / f"gen{gen}"
    for variant_dir in variant_dirs:
        variant_id = variant_dir.name
        answers = {
            p.stem: read_text(p)
            for p in variant_dir.glob("*.md")
        }
        user = (
            f"## JD components\n{components}\n\n"
            f"## Form questions\n{questions}\n\n"
            f"## Candidate's answers\n{answers}\n\n"
            f"## Tailored CV\n{cv_text}\n"
        )
        for judge in JUDGES:
            system = SYSTEM_TEMPLATE.format(persona=judge["persona"])
            result = call(system, user, temperature=judge["temperature"], max_tokens=4096)
            record = parse_json(result)
            record["variant_id"] = variant_id
            record["judge_id"] = judge["id"]
            write_json(evals_dir / f"{variant_id}_{judge['id']}.json", record)
        print(f"Judged {variant_id} ({len(JUDGES)} judges).")


if __name__ == "__main__":
    main()
