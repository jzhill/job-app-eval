"""Stage 14: Directed Iteration.

Usage: python scripts/plan_next_gen.py --gen 1

Reads rounds/gen<N>/direction.md (Jeremy's freeform notes + frontmatter)
plus summary.md/preferences.md, and writes
rounds/gen<N+1>/round_config.json. Not a fully automatic mutation loop --
Jeremy approves or adjusts the result before the next generation runs.
"""

import sys
from pathlib import Path

import frontmatter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/_common.py, one level up from deprecated/
from _common import call, gen_dir, parse_json, read_text, write_json

SYSTEM = """You read a candidate's freeform notes after reviewing a round
of application drafts, and extract two lists from the prose: specific
phrases or points to retain verbatim in the next round, and specific
things to drop/cut. Only include items the notes actually state -- don't
infer additional ones. Output ONLY a JSON object:
{"retain_verbatim": ["..."], "drop": ["..."]}"""


def main():
    if "--gen" not in sys.argv:
        raise SystemExit("Usage: python scripts/plan_next_gen.py --gen <N>")
    gen = int(sys.argv[sys.argv.index("--gen") + 1])

    direction_path = gen_dir("rounds", gen) / "direction.md"
    if not direction_path.exists():
        raise SystemExit(f"output/rounds/gen{gen}/direction.md not found -- do the sniff check first.")

    post = frontmatter.loads(read_text(direction_path))
    mode = post.get("next_mode", "exploration")
    variant_count = post.get("next_variant_count") or 8

    extracted = parse_json(call(SYSTEM, post.content, effort="high"))

    config = {
        "mode": mode,
        "variant_count": variant_count,
        "carried_forward_commentary": f"rounds/gen{gen}/direction.md",
        "retain_verbatim": extracted["retain_verbatim"],
        "drop": extracted["drop"],
    }
    write_json(gen_dir("rounds", gen + 1) / "round_config.json", config)
    print(f"Wrote output/rounds/gen{gen + 1}/round_config.json ({mode}, {variant_count} variant(s)).")
    print("Review before running generate_drafts.py for the next round.")


if __name__ == "__main__":
    main()
