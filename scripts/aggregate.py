"""Stage 14: Aggregation (numeric half only).

Usage: python scripts/aggregate.py --gen 1

Computes the mean/variance rollups directly -- no LLM needed for
arithmetic, no Anthropic API key required. Writes summary.json and the
numeric-ranking half of summary.md. The qualitative "what recurs across
judges" synthesis is done by the agent, in-context, reading the eval files
directly -- see design doc Stage 14. This script used to make an LLM call
for that synthesis too; that moved in-context along with every other
non-Stage-11 stage.
"""

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OUTPUT, gen_dir, read_json, read_text, write_json, write_text

SCORES_LONG_COLUMNS = ["gen", "variant_id", "judge_id", "category", "item_id", "score", "comment"]

# Composite score weights, agreed with Jeremy 2026-09-07: vibe/cv/jd/application
# on a 0-100 scale each (1-5 fields rescaled via (mean-1)/4*100), jd and
# application are equal-weighted across their three sections / four questions
# respectively (not weighted by item count within each).
COMPOSITE_WEIGHTS = {"vibe": 0.2, "cv": 0.1, "jd": 0.3, "application": 0.4}
SECTIONS = ["required_qualifications", "preferred_qualifications", "core_responsibilities"]


def rescale_1_5_to_100(mean_1_5: float) -> float:
    return (mean_1_5 - 1) / 4 * 100

RECURRING_HEADING = "## Recurring findings across judges"
RECURRING_PLACEHOLDER = (
    f"{RECURRING_HEADING}\n\n"
    "*(agent: fill this in by reading output/evals/gen{gen}/v*_judge_*.json "
    "directly and pulling out comments that recur across >=2 judges -- "
    "see design doc Stage 14)*"
)


def existing_recurring_section(gen: int) -> str | None:
    """Return a prior summary.md's '## Recurring findings' section if the
    agent already replaced the placeholder with real synthesis -- so
    rerunning this script (e.g. after a late/corrected judge eval file)
    doesn't clobber that in-context work back to the placeholder."""
    path = gen_dir("evals", gen) / "summary.md"
    if not path.exists():
        return None
    text = read_text(path)
    idx = text.find(RECURRING_HEADING)
    if idx == -1:
        return None
    section = text[idx:].rstrip("\n")
    if section == RECURRING_PLACEHOLDER.format(gen=gen):
        return None
    return section


def load_evals(gen: int):
    evals_dir = gen_dir("evals", gen)
    records = []
    for path in sorted(evals_dir.glob("*_judge_*.json")):
        records.append(read_json(path))
    return records


SECTION_BY_COMPONENT = {}


def load_section_map():
    components = read_json(OUTPUT / "jd_components.json")
    for section, items in components.items():
        if isinstance(items, list):
            for item in items:
                SECTION_BY_COMPONENT[item["id"]] = section


def write_scores_long(gen: int, records: list[dict]) -> None:
    """One row per individual judge score -- every component, question, CV,
    and vibe score across every (variant, judge) pair, in long/tidy format
    for pivoting in R/pandas or feeding a chart directly. Not a summary --
    scores.json/summary.md already do the rollup; this is the raw material."""
    rows = []
    for record in records:
        variant_id, judge_id = record["variant_id"], record["judge_id"]
        for component_id, entry in record["component_scores"].items():
            category = SECTION_BY_COMPONENT.get(component_id, "unknown_component")
            rows.append([gen, variant_id, judge_id, category, component_id, entry["score"], entry["comment"]])
        for question_id, entry in record["question_scores"].items():
            rows.append([gen, variant_id, judge_id, "question", question_id, entry["score"], entry["comment"]])
        cv = record["cv_evaluation"]
        rows.append([gen, variant_id, judge_id, "cv", "cv_evaluation", cv["score"], cv["comment"]])
        rows.append([gen, variant_id, judge_id, "vibe", "vibe_score", record["vibe_score"], record.get("overall_assessment", "")])

    path = gen_dir("evals", gen) / "scores_long.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(SCORES_LONG_COLUMNS)
        writer.writerows(rows)


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
        vibe_scores = []
        cv_scores = []
        for record in judge_records:
            vibe_scores.append(record["vibe_score"])
            cv_scores.append(record["cv_evaluation"]["score"])
            for component_id, entry in record["component_scores"].items():
                component_scores[component_id].append(entry["score"])
                section = SECTION_BY_COMPONENT.get(component_id)
                if section:
                    section_scores[section].append(entry["score"])
            for question_id, entry in record["question_scores"].items():
                question_scores[question_id].append(entry["score"])

        mean_vibe = round(statistics.mean(vibe_scores), 2)
        section_means = {
            k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
            for k, v in section_scores.items()
        }
        question_means = {
            k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
            for k, v in question_scores.items()
        }
        cv_mean = round(statistics.mean(cv_scores), 2)

        # Composite score inputs: jd/application are the mean of their
        # sections'/questions' own means (equal weight per section/question,
        # not per underlying item -- see COMPOSITE_WEIGHTS above).
        jd_norm = rescale_1_5_to_100(statistics.mean(s["mean"] for s in section_means.values())) if section_means else None
        application_norm = rescale_1_5_to_100(statistics.mean(q["mean"] for q in question_means.values())) if question_means else None
        cv_norm = rescale_1_5_to_100(cv_mean)
        composite_score = None
        if jd_norm is not None and application_norm is not None:
            composite_score = round(
                COMPOSITE_WEIGHTS["vibe"] * mean_vibe
                + COMPOSITE_WEIGHTS["cv"] * cv_norm
                + COMPOSITE_WEIGHTS["jd"] * jd_norm
                + COMPOSITE_WEIGHTS["application"] * application_norm,
                2,
            )

        variant_summaries[variant_id] = {
            "mean_vibe_score": mean_vibe,
            "cv_score": {"mean": cv_mean, "n": len(cv_scores)},
            "composite_score": composite_score,
            "component_scores": {
                k: {"mean": round(statistics.mean(v), 2), "n": len(v)}
                for k, v in component_scores.items()
            },
            "section_scores": section_means,
            "question_scores": question_means,
        }

    ranked = sorted(variant_summaries.items(), key=lambda kv: -kv[1]["mean_vibe_score"])
    summary_json = {"variants": dict(ranked)}
    write_json(gen_dir("evals", gen) / "summary.json", summary_json)
    write_scores_long(gen, records)

    preserved = existing_recurring_section(gen)

    top = ranked[:3]
    lines = [f"# Summary — gen{gen}\n", "## Top variants (ranked by vibe_score)\n"]
    for variant_id, data in top:
        composite = data["composite_score"]
        composite_str = f", composite {composite}/100" if composite is not None else ""
        lines.append(f"- **{variant_id}**: vibe {data['mean_vibe_score']}/100{composite_str}")
    lines.append(
        "\n(`composite_score` weights: "
        + ", ".join(f"{k} {v}" for k, v in COMPOSITE_WEIGHTS.items())
        + " -- jd/application equal-weighted across sections/questions, see `aggregate.py`.)"
    )
    lines.append("\n" + (preserved if preserved else RECURRING_PLACEHOLDER.format(gen=gen)))
    write_text(gen_dir("evals", gen) / "summary.md", "\n".join(lines))

    print(f"Wrote output/evals/gen{gen}/summary.json, summary.md, and scores_long.csv.")
    print(f"Top variant: {top[0][0]} ({top[0][1]['mean_vibe_score']}/100)")
    if preserved:
        print("Preserved existing recurring-findings synthesis from prior summary.md.")
    else:
        print("Numeric rollup only -- add the recurring-findings synthesis in-context, per design doc Stage 14.")


if __name__ == "__main__":
    main()
