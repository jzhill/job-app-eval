"""Stage 13: Judge Panel Evaluation.

Usage: python scripts/run_judges.py --gen 1

Only runs in exploration-mode rounds -- skipped (with a message) if the
round's config says convergence. Each judge produces one evaluation per
variant covering the whole application package (all question drafts +
the tailored CV), not one evaluation per question. Judge calls run
concurrently (bounded thread pool) -- each (variant, judge) call is fully
independent, no shared state or data dependency between them.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DEFAULT_MODEL, OUTPUT, call, gen_dir, parse_json, read_json, read_text, write_json

# Bounded, not unlimited -- avoids tripping the Anthropic API's per-minute
# rate limits, which unbounded concurrency across all variants x judges risks.
MAX_WORKERS = 5

# Diversity comes from persona (all three) and model (domain_expert uses a
# different model than the generator, to reduce self-preference bias) --
# not from temperature, which the Messages API no longer exposes.
JUDGES = [
    {"id": "judge_skeptical_senior",
     "persona": "You are a skeptical senior reviewer. You've seen hundreds of applications and are quick to spot vague claims, generic phrasing, and unsupported assertions.",
     "model": DEFAULT_MODEL},
    {"id": "judge_warm_screener",
     "persona": "You are a warm first-read screener. You're looking for genuine enthusiasm and fit, and give candidates the benefit of the doubt on rough edges, while still noting real gaps.",
     "model": DEFAULT_MODEL},
    {"id": "judge_domain_expert",
     "persona": "You are a technically literate domain expert in this specific field. You test whether the candidate demonstrates real, specific knowledge of the field's landscape, not just generic competence language.",
     "model": "claude-opus-5"},
]

SYSTEM_TEMPLATE = """{persona}

Score this job application (all question answers + the tailored CV) as
one package against the JD components and form questions provided.

## Marking guide (follow this for scoring, ids, and outcome rule)
{marking_guide}

Output ONLY a JSON object:
{{"component_scores": {{"<jd_component_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"question_scores": {{"<question_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"cv_evaluation": {{"score": 1-5, "comment": "..."}},
"style_fidelity": {{"score": 1-5, "comment": "...", "weight": "low -- sanity check only, not blended into content scores"}},
"overall_score": 1-5, "overall_outcome": "screen_in"|"screen_out",
"overall_candidate_feedback": "..."}}
Score every JD component and every question given, even briefly."""

REQUIRED_KEYS = [
    "component_scores", "question_scores", "cv_evaluation", "style_fidelity",
    "overall_score", "overall_outcome", "overall_candidate_feedback",
]


def validate(record: dict) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in record]
    if missing:
        raise ValueError(f"missing required key(s): {missing}")


def judge_variant(variant_id: str, user: str, judge: dict, marking_guide: str) -> dict:
    system = SYSTEM_TEMPLATE.format(persona=judge["persona"], marking_guide=marking_guide)
    max_attempts = 5
    for attempt in range(max_attempts):
        result = call(system, user, model=judge["model"], effort="high", max_tokens=16000)
        try:
            record = parse_json(result)
            validate(record)
            record["variant_id"] = variant_id
            record["judge_id"] = judge["id"]
            return record
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == max_attempts - 1:
                raise
            print(f"  {judge['id']} on {variant_id}: {e}, retrying ({attempt + 1}/{max_attempts - 1})...")


def main():
    if "--gen" not in sys.argv:
        raise SystemExit("Usage: python scripts/run_judges.py --gen <N>")
    gen = int(sys.argv[sys.argv.index("--gen") + 1])

    config_path = gen_dir("rounds", gen) / "round_config.json"
    if config_path.exists() and read_json(config_path)["mode"] == "convergence":
        print(f"gen{gen} is a convergence round -- no judge panel runs.")
        return

    marking_guide_path = OUTPUT / "marking_guide.md"
    if not marking_guide_path.exists():
        raise SystemExit(
            f"{marking_guide_path} not found -- Stage 3 (marking guide "
            "co-creation) must run before judges can be scored."
        )
    marking_guide = read_text(marking_guide_path)

    components = read_json(OUTPUT / "jd_components.json")
    questions = read_json(OUTPUT / "form_questions.json")
    cv_path = OUTPUT / "cv_tailored.md"
    cv_text = read_text(cv_path) if cv_path.exists() else "(no tailored CV yet)"

    drafts_dir = gen_dir("drafts", gen)
    variant_dirs = sorted(p for p in drafts_dir.iterdir() if p.is_dir())

    evals_dir = gen_dir("evals", gen)

    tasks = []
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
            tasks.append((variant_id, user, judge))

    failures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(judge_variant, variant_id, user, judge, marking_guide): (variant_id, judge["id"])
            for variant_id, user, judge in tasks
        }
        for future in as_completed(futures):
            variant_id, judge_id = futures[future]
            try:
                record = future.result()
            except Exception as e:
                print(f"FAILED: {judge_id} on {variant_id}: {e}")
                failures.append(f"{variant_id}/{judge_id}")
                continue
            write_json(evals_dir / f"{variant_id}_{judge_id}.json", record)
            print(f"Judged {variant_id} x {judge_id}.")

    if failures:
        raise SystemExit(f"{len(failures)} judge call(s) failed after retries: {failures}")


if __name__ == "__main__":
    main()
