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

import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OUTPUT, gen_dir, read_json, read_text, write_json, write_text

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
        vibe_scores = []
        for record in judge_records:
            vibe_scores.append(record["vibe_score"])
            for component_id, entry in record["component_scores"].items():
                component_scores[component_id].append(entry["score"])
                section = SECTION_BY_COMPONENT.get(component_id)
                if section:
                    section_scores[section].append(entry["score"])
            for question_id, entry in record["question_scores"].items():
                question_scores[question_id].append(entry["score"])

        variant_summaries[variant_id] = {
            "mean_vibe_score": round(statistics.mean(vibe_scores), 2),
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

    ranked = sorted(variant_summaries.items(), key=lambda kv: -kv[1]["mean_vibe_score"])
    summary_json = {"variants": dict(ranked)}
    write_json(gen_dir("evals", gen) / "summary.json", summary_json)

    preserved = existing_recurring_section(gen)

    top = ranked[:3]
    lines = [f"# Summary — gen{gen}\n", "## Top variants\n"]
    for variant_id, data in top:
        lines.append(f"- **{variant_id}**: {data['mean_vibe_score']}/100")
    lines.append("\n" + (preserved if preserved else RECURRING_PLACEHOLDER.format(gen=gen)))
    write_text(gen_dir("evals", gen) / "summary.md", "\n".join(lines))

    print(f"Wrote output/evals/gen{gen}/summary.json and summary.md.")
    print(f"Top variant: {top[0][0]} ({top[0][1]['mean_vibe_score']}/100)")
    if preserved:
        print("Preserved existing recurring-findings synthesis from prior summary.md.")
    else:
        print("Numeric rollup only -- add the recurring-findings synthesis in-context, per design doc Stage 14.")


if __name__ == "__main__":
    main()
