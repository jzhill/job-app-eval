"""Stage 10: Draft Generation.

Usage: python scripts/generate_drafts.py --gen 1

Generalized from one essay to N form questions -- each variant is one
coherent bundle of answers across all questions, generated together so
answers don't repeat or collide. Mode-aware: exploration produces a
variant set for judging; convergence produces one refined draft and
skips judging entirely for that round.

If rounds/gen<N>/round_config.json doesn't exist (true for gen 1), default
to exploration mode with 8 variants and no carried-forward direction.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/_common.py, one level up from deprecated/
from _common import INPUT, OUTPUT, call, parse_json, read_json, read_text, write_json, write_text

AXES = [
    {"structural_lead": "narrative", "emphasis": "balanced"},
    {"structural_lead": "evidence", "emphasis": "balanced"},
    {"structural_lead": "argument", "emphasis": "balanced"},
    {"structural_lead": "narrative", "emphasis": "primary_strength_forward"},
    {"structural_lead": "evidence", "emphasis": "primary_strength_forward"},
    {"structural_lead": "argument", "emphasis": "primary_strength_forward"},
    {"structural_lead": "narrative", "emphasis": "secondary_strength_forward"},
    {"structural_lead": "evidence", "emphasis": "secondary_strength_forward"},
    {"structural_lead": "argument", "emphasis": "secondary_strength_forward"},
    {"structural_lead": "narrative", "emphasis": "balanced"},
]

SYSTEM = """You draft answers to a job application's open-text questions,
as one coherent bundle -- the same candidate voice across all questions,
no repeated points between them.

Ground every answer in the tagged context fragments provided (only use
material that's actually there; the interview report and external
references are additional material to draw on). Match the voice profile
if one is provided. Respect each question's stated word/character limit.
Apply the given structural lead and emphasis axis. Apply any hard
constraints in preferences, and any retain-verbatim / drop instructions
from the prior round's direction.

Output ONLY a JSON object: {"<question_id>": "<answer text>", ...} with
one key per question id given."""


def load_optional(path: Path, default=""):
    return read_text(path) if path.exists() else default


def build_round_config(gen: int) -> dict:
    config_path = OUTPUT / "rounds" / f"gen{gen}" / "round_config.json"
    if config_path.exists():
        return read_json(config_path)
    return {"mode": "exploration", "variant_count": 8, "carried_forward_commentary": None,
            "retain_verbatim": [], "drop": []}


def generate_variant(user_context: str, axis: dict) -> dict:
    user = f"{user_context}\n\n## Axis for this variant\n{axis}\n"
    result = call(SYSTEM, user, max_tokens=4096)
    return parse_json(result)


def main():
    if "--gen" not in sys.argv:
        raise SystemExit("Usage: python scripts/generate_drafts.py --gen <N>")
    gen = int(sys.argv[sys.argv.index("--gen") + 1])

    config = build_round_config(gen)
    components = read_json(OUTPUT / "jd_components.json")
    questions = read_json(OUTPUT / "form_questions.json")
    tagged = read_json(OUTPUT / "tagged_context.json")
    interview = load_optional(OUTPUT / "interview_report.md", "(none)")
    references = load_optional(OUTPUT / "external_references.md", "(none)")
    preferences = load_optional(INPUT / "preferences.md", "(none)")
    voice_profile = load_optional(OUTPUT / "voice_profile.md", "(no voice profile yet -- write naturally)")

    direction = "(none -- this is generation 1)"
    if config.get("carried_forward_commentary"):
        direction_path = OUTPUT / config["carried_forward_commentary"]
        if direction_path.exists():
            direction = read_text(direction_path)
    if config.get("retain_verbatim") or config.get("drop"):
        direction += f"\n\nRetain verbatim: {config['retain_verbatim']}\nDrop: {config['drop']}"

    user_context = (
        f"## JD components\n{components}\n\n"
        f"## Form questions\n{questions}\n\n"
        f"## Tagged context fragments\n{tagged['fragments']}\n\n"
        f"## Interview report\n{interview}\n\n"
        f"## External references\n{references}\n\n"
        f"## Preferences / hard constraints\n{preferences}\n\n"
        f"## Voice profile\n{voice_profile}\n\n"
        f"## Direction from prior round\n{direction}\n"
    )

    mode = config["mode"]
    variant_count = 1 if mode == "convergence" else config["variant_count"]
    print(f"Generating {variant_count} variant(s) for gen{gen} in {mode} mode.")

    for i in range(variant_count):
        variant_id = f"v{i + 1:02d}"
        axis = {"mode": "convergence"} if mode == "convergence" else AXES[i % len(AXES)]
        answers = generate_variant(user_context, axis)

        variant_dir = OUTPUT / "drafts" / f"gen{gen}" / variant_id
        for question_id, text in answers.items():
            write_text(variant_dir / f"{question_id}.md", text)
        write_json(variant_dir / f"{variant_id}.meta.json", {"axis": axis})
        print(f"  wrote output/drafts/gen{gen}/{variant_id}/")


if __name__ == "__main__":
    main()
