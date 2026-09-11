"""Stage 13: Judge Panel Evaluation.

Usage: python scripts/run_judges.py --gen 1

Skipped (with a message) if the round's config says convergence -- runs
for exploration and comparison modes alike. Each judge produces one evaluation per
variant covering the whole application package (all question drafts +
the tailored CV), not one evaluation per question. Judge calls run
concurrently (bounded thread pool) -- each (variant, judge) call is fully
independent, no shared state or data dependency between them.
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DEFAULT_MODEL, INPUT, OUTPUT, call, gen_dir, parse_json, read_json, read_text, write_json

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
one package against the full job posting, its structured JD-component
breakdown, and the form questions provided -- the way a real screener
would read the posting itself, not just a checklist derived from it.

## Marking guide (follow this for scoring, ids, and outcome rule)
{marking_guide}

Output ONLY a JSON object:
{{"component_scores": {{"<jd_component_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"section_assessments": {{"required_qualifications": "...", "preferred_qualifications": "...", "core_responsibilities": "..."}},
"question_scores": {{"<question_id>": {{"score": 1-5, "comment": "..."}}, ...}},
"cv_evaluation": {{"score": 1-5, "comment": "..."}},
"vibe_score": 0-100, "overall_outcome": "screen_in"|"borderline"|"screen_out",
"overall_assessment": "...", "candidate_feedback": "..."}}
Score every required/preferred qualification and core responsibility, and
every question, even briefly. Do not score mission_signals items
individually -- they're context only for the vibe score and assessments.
component_scores MUST have exactly {n_components} entries: {n_required}
required_qualifications + {n_preferred} preferred_qualifications +
{n_responsibilities} core_responsibilities -- do not stop after the
required_qualifications section, all three categories must be fully
scored before you close the JSON object."""

SECTIONS = ["required_qualifications", "preferred_qualifications", "core_responsibilities"]

REQUIRED_KEYS = [
    "component_scores", "section_assessments", "question_scores", "cv_evaluation",
    "vibe_score", "overall_outcome", "overall_assessment", "candidate_feedback",
]


SECTION_HEADING = re.compile(r"^##\s*\[(\w+)\][^\n]*$", re.MULTILINE)


def parse_answer_sections(text: str, valid_question_ids: set) -> dict[str, str]:
    """Split a single-file draft (application.md) into {question_id: text}
    by its '## [question_id] ...' headings -- deterministic, code-side
    parsing rather than leaving the id/text mapping to the judge."""
    matches = list(SECTION_HEADING.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = text[start:end].strip()
    found = set(sections)
    if found != valid_question_ids:
        raise ValueError(
            "draft file's '## [question_id]' headings don't match form_questions.json -- "
            f"extra: {sorted(found - valid_question_ids)}, missing: {sorted(valid_question_ids - found)}"
        )
    return sections


def extract_valid_ids(components: dict, questions: dict) -> tuple[set, set]:
    component_ids = {item["id"] for section in SECTIONS for item in components[section]}
    question_ids = {q["id"] for q in questions["questions"]}
    return component_ids, question_ids


def validate(record: dict, valid_component_ids: set, valid_question_ids: set) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in record]
    if missing:
        raise ValueError(f"missing required key(s): {missing}")

    component_keys = set(record["component_scores"].keys())
    if component_keys != valid_component_ids:
        raise ValueError(
            "component_scores keys don't match jd_components.json -- "
            f"extra: {sorted(component_keys - valid_component_ids)}, "
            f"missing: {sorted(valid_component_ids - component_keys)}"
        )

    section_keys = set(record["section_assessments"].keys())
    if section_keys != set(SECTIONS):
        raise ValueError(
            "section_assessments keys don't match the scored sections -- "
            f"extra: {sorted(section_keys - set(SECTIONS))}, "
            f"missing: {sorted(set(SECTIONS) - section_keys)}"
        )

    question_keys = set(record["question_scores"].keys())
    if question_keys != valid_question_ids:
        raise ValueError(
            "question_scores keys don't match form_questions.json -- "
            f"extra: {sorted(question_keys - valid_question_ids)}, "
            f"missing: {sorted(valid_question_ids - question_keys)}"
        )


def judge_variant(variant_id: str, user: str, judge: dict, marking_guide: str,
                   valid_component_ids: set, valid_question_ids: set,
                   section_counts: dict) -> dict:
    system = SYSTEM_TEMPLATE.format(
        persona=judge["persona"], marking_guide=marking_guide,
        n_components=sum(section_counts.values()),
        n_required=section_counts["required_qualifications"],
        n_preferred=section_counts["preferred_qualifications"],
        n_responsibilities=section_counts["core_responsibilities"],
    )
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            result = call(system, user, model=judge["model"], effort="high", max_tokens=32000)
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as e:
            if attempt == max_attempts - 1:
                raise
            wait = 2 ** attempt
            print(f"  {judge['id']} on {variant_id}: {type(e).__name__}, "
                  f"backing off {wait}s ({attempt + 1}/{max_attempts - 1})...")
            time.sleep(wait)
            continue
        try:
            record = parse_json(result)
            validate(record, valid_component_ids, valid_question_ids)
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

    job_posting = read_text(INPUT / "job_posting.md")
    components = read_json(OUTPUT / "jd_components.json")
    questions = read_json(OUTPUT / "form_questions.json")
    valid_component_ids, valid_question_ids = extract_valid_ids(components, questions)
    section_counts = {section: len(components[section]) for section in SECTIONS}
    cv_path = OUTPUT / "cv_tailored.md"
    cv_text = read_text(cv_path) if cv_path.exists() else "(no tailored CV yet)"

    drafts_dir = gen_dir("drafts", gen)
    draft_paths = sorted(drafts_dir.glob("*.md"))

    evals_dir = gen_dir("evals", gen)

    tasks = []
    for draft_path in draft_paths:
        variant_id = draft_path.stem
        answers = parse_answer_sections(read_text(draft_path), valid_question_ids)
        user = (
            f"## Job posting (as the candidate would have read it)\n{job_posting}\n\n"
            f"## JD components (structured decomposition of the posting above, for scoring ids)\n{components}\n\n"
            f"## Form questions\n{questions}\n\n"
            f"## Candidate's answers\n{answers}\n\n"
            f"## Tailored CV\n{cv_text}\n"
        )
        for judge in JUDGES:
            if (evals_dir / f"{variant_id}_{judge['id']}.json").exists():
                print(f"Skipping {variant_id} x {judge['id']} -- already judged.")
                continue
            tasks.append((variant_id, user, judge))

    failures = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(judge_variant, variant_id, user, judge, marking_guide,
                        valid_component_ids, valid_question_ids, section_counts): (variant_id, judge["id"])
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
