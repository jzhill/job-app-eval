"""Stage 9: CV Tailoring.

Single-pass, not a variant tournament -- CVs are factual/structured and
lower voice-sensitivity than an essay, so overclaim risk is guarded
directly via a claims_checklist rather than explored stylistically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/_common.py, one level up from deprecated/
from _common import INPUT, OUTPUT, call, parse_json, read_cv_text, read_json, read_text, write_json, write_text

SYSTEM = """You tailor a CV for a specific job, in one pass.

Reorder and re-emphasize bullets and the summary to foreground what
matches the JD components most, without inventing anything. Every factual
claim in the tailored CV must be traceable to a specific fragment in the
tagged context provided (only fragments with origin "essay_response" or
"interview" count as support -- never "external_reference", since a claim
about the candidate can't be supported by something they merely read).
Preserve the CV's existing section structure.

Also apply any hard constraints listed in preferences (e.g. framing
corrections that must never be reverted).

Output ONLY a JSON object:
{"cv_tailored": "<the full tailored CV as markdown>",
 "changes": [{"section": "...", "change": "...", "reason": "..."}],
 "claims_checklist": [{"claim": "...", "traceable_to": "<fragment id or null>",
 "overclaim_risk": {"score": 1-5, "comment": "..."}}]}
Score overclaim_risk 1 (fully supported) to 5 (unsupported / matches a
known overclaim pattern -- do not include)."""


def main():
    components = read_json(OUTPUT / "jd_components.json")
    tagged = read_json(OUTPUT / "tagged_context.json")
    cv_text = read_cv_text()
    preferences_path = INPUT / "preferences.md"
    preferences = read_text(preferences_path) if preferences_path.exists() else "(none)"

    user = (
        f"## JD components\n{components}\n\n"
        f"## Tagged context fragments\n{tagged['fragments']}\n\n"
        f"## Preferences / hard constraints\n{preferences}\n\n"
        f"## Current CV\n{cv_text}\n"
    )
    result = call(SYSTEM, user, effort="high", max_tokens=8192)
    data = parse_json(result)

    write_text(OUTPUT / "cv_tailored.md", data.pop("cv_tailored"))
    write_json(OUTPUT / "cv_tailoring_notes.json", data)

    print("Wrote output/cv_tailored.md and output/cv_tailoring_notes.json.")
    flagged = [c for c in data["claims_checklist"] if c["overclaim_risk"]["score"] >= 4]
    if flagged:
        print(f"{len(flagged)} claim(s) flagged high overclaim risk -- review before using:")
        for claim in flagged:
            print(f"  {claim['claim']}")


if __name__ == "__main__":
    main()
