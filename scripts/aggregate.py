"""Stage 12: Aggregation.

Usage: python scripts/aggregate.py --gen 1

Numeric rollups computed directly (no LLM needed for arithmetic); the
qualitative "what recurs across judges" synthesis uses one LLM call,
mirroring the manual 9-eval synthesis this pipeline automates.
"""

import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OUTPUT, call, gen_dir, read_json, write_json, write_text

SYNTHESIZE_SYSTEM = """You're given numeric scores and comments from
multiple judges across multiple variants of a job application. Identify
qualitative comments that recur across 2 or more judges (possibly on
different variants) -- these are the highest-value findings, since a
numeric score tells you something's wrong but a recurring comment tells
you what. Output a short markdown list, most-repeated first. Don't invent
patterns that aren't really there -- if nothing clearly recurs, say so."""


def load_evals(gen: int):
    evals_dir = gen_dir("evals", gen)
    records = []
    for path in sorted(evals_dir.glob("v*_judge_*.json")):
        records.append(read_json(path))
    return records


SECTION_BY_COMPONENT = {}


def load_section_map():
    components = read_json(OUTPUT / "jd_components.json")
    for section, items in components.items():
        if isinstance(items, list):
            for item in items:
                SECTION_BY_COMPONENT[item["id"]] = section


def main():
    if "--gen" not in sys.argv:
        raise SystemExit("Usage: python scripts/aggregate.py --gen <N>")
    gen = int(sys.argv[sys.argv.index("--gen") + 1])

    records = load_evals(gen)
    if not records:
        raise SystemExit(f"No evals found in output/evals/gen{gen}/ -- run run_judges.py first.")
    load_section_map()

    by_variant = defaultdict(list)
    for record in records:
        by_variant[record["variant_id"]].append(record)

    variant_summaries = {}
    for variant_id, judge_records in by_variant.items():
        component_scores = defaultdict(list)
        section_scores = defaultdict(list)
        question_scores = defaultdict(list)
        overall_scores = []
        for record in judge_records:
            overall_scores.append(record["overall_score"])
            for component_id, entry in record["component_scores"].items():
                component_scores[component_id].append(entry["score"])
                section = SECTION_BY_COMPONENT.get(component_id)
                if section:
                    section_scores[section].append(entry["score"])
            for question_id, entry in record["question_scores"].items():
                question_scores[question_id].append(entry["score"])

        variant_summaries[variant_id] = {
            "mean_overall_score": round(statistics.mean(overall_scores), 2),
            "component_scores": {
                k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
                for k, v in component_scores.items()
            },
            "section_scores": {
                k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
                for k, v in section_scores.items()
            },
            "question_scores": {
                k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
                for k, v in question_scores.items()
            },
        }

    ranked = sorted(variant_summaries.items(), key=lambda kv: -kv[1]["mean_overall_score"])
    summary_json = {"variants": dict(ranked)}
    write_json(gen_dir("evals", gen) / "summary.json", summary_json)

    all_comments = [
        {"variant_id": r["variant_id"], "judge_id": r["judge_id"],
         "overall_candidate_feedback": r["overall_candidate_feedback"]}
        for r in records
    ]
    recurring = call(SYNTHESIZE_SYSTEM, str(all_comments), temperature=0.0)

    top = ranked[:3]
    lines = [f"# Summary — gen{gen}\n", "## Top variants\n"]
    for variant_id, data in top:
        lines.append(f"- **{variant_id}**: {data['mean_overall_score']}/5")
    lines.append("\n## Recurring findings across judges\n")
    lines.append(recurring)
    write_text(gen_dir("evals", gen) / "summary.md", "\n".join(lines))

    print(f"Wrote output/evals/gen{gen}/summary.json and summary.md.")
    print(f"Top variant: {top[0][0]} ({top[0][1]['mean_overall_score']}/5)")


if __name__ == "__main__":
    main()
