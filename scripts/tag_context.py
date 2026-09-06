"""Stage 5: Context Mapping.

Maps input/essay_response.md and external_references.md onto
jd_components.json / form_questions.json -> tagged_context.json, plus a
tagged_context.md rendering for human review. Flags low-confidence
mappings for priority review -- Jeremy is approving an LLM's
interpretation of his own words, not his own tagging.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OUTPUT, call, parse_json, read_json, read_text, require_input, write_json, write_text

SYSTEM = """You map fragments of source text onto a job description's
components and an application form's questions.

You'll receive: the JD components (grouped by category), the form
questions, Jeremy's free-written essay response, and a digest of external
references he's collected.

Break the essay response into coherent fragments (a fragment can be a
sentence, a few sentences, or a paragraph -- whatever holds one coherent
idea). For each fragment, identify which JD component ids it provides
evidence for (if any) and which form question ids it's relevant to (if
any). Also do this for each external-reference entry, but tag its origin
as "external_reference" instead of "essay_response" -- these can support
JD components (e.g. mission signals) but should rarely if ever be tagged
to form questions, since they aren't the candidate's own material.

Rate your confidence per fragment as "high", "medium", or "low". Then list
JD components with weak or no supporting fragments as coverage_gaps.

Output ONLY a JSON object:
{"fragments": [{"id": "frag_NNN", "source_excerpt": "<exact text>",
"jd_component_ids": [...], "form_question_ids": [...],
"confidence": "high"|"medium"|"low",
"origin": "essay_response"|"external_reference"}],
"coverage_gaps": [{"jd_component_id": "...", "status": "weak"|"none"}]}"""


def render_markdown(tagged: dict, components: dict) -> str:
    by_component = {}
    for fragment in tagged["fragments"]:
        for component_id in fragment.get("jd_component_ids", []):
            by_component.setdefault(component_id, []).append(fragment)

    lines = ["# Tagged Context (auto-rendered from tagged_context.json -- do not edit directly)\n"]
    for category, items in components.items():
        if not isinstance(items, list):
            continue
        for item in items:
            component_id = item["id"]
            lines.append(f"## {component_id} — {item['text']}")
            for fragment in by_component.get(component_id, []):
                flag = " [LOW CONFIDENCE]" if fragment["confidence"] == "low" else ""
                lines.append(f"- ({fragment['origin']}{flag}) {fragment['source_excerpt']}")
            if component_id not in by_component:
                lines.append("- *(no supporting material found)*")
            lines.append("")

    gaps = tagged.get("coverage_gaps", [])
    if gaps:
        lines.append("## Coverage gaps")
        for gap in gaps:
            lines.append(f"- {gap['jd_component_id']}: {gap['status']}")

    return "\n".join(lines)


def main():
    essay = read_text(require_input("essay_response.md"))
    refs_path = OUTPUT / "external_references.md"
    refs = read_text(refs_path) if refs_path.exists() else "(none)"
    components = read_json(OUTPUT / "jd_components.json")
    questions = read_json(OUTPUT / "form_questions.json")

    user = (
        f"## JD components\n{components}\n\n"
        f"## Form questions\n{questions}\n\n"
        f"## Essay response\n{essay}\n\n"
        f"## External references\n{refs}\n"
    )
    result = call(SYSTEM, user, temperature=0.0, max_tokens=8192)
    tagged = parse_json(result)
    write_json(OUTPUT / "tagged_context.json", tagged)
    write_text(OUTPUT / "tagged_context.md", render_markdown(tagged, components))

    low_confidence = [f for f in tagged["fragments"] if f["confidence"] == "low"]
    print("Wrote output/tagged_context.json and output/tagged_context.md.")
    if low_confidence:
        print(f"{len(low_confidence)} low-confidence mapping(s) -- review these first:")
        for fragment in low_confidence:
            print(f"  {fragment['id']}: {fragment['source_excerpt'][:80]}")


if __name__ == "__main__":
    main()
