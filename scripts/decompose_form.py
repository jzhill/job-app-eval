"""Stage 2: Form Decomposition.

Default: itemize input/job_posting.md (the application-form portion)
-> form_itemised.md, then stop. Review against the actual form yourself.

--decompose: read the (reviewed) form_itemised.md -> form_questions.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, call, parse_json, read_text, require_input, write_json, write_text

ITEMIZE_SYSTEM = """You itemize an application form into a numbered list,
verbatim. The source text may contain both a job description and an
application form (common on ATS platforms like Greenhouse) -- itemize only
the application-form portion: the actual fields/questions a candidate fills
in, in the order they appear. For each field, capture: the exact label/prompt
text, whether it's required, the field type if apparent (text, multi-line
text, select, file upload), and any stated word/character limit or
description text verbatim. Group fields under "## Section: <name>" headings
matching the form's own structure. Standard demographic/EEOC compliance
boilerplate (gender, ethnicity, veteran/disability status) should be
labeled as its own section and characterized briefly rather than quoted
field-by-field, since it's generic and not role-specific -- but don't drop
it silently, note that it exists. Number items continuously."""

DECOMPOSE_SYSTEM = """You extract the open-ended content questions from an
itemised application form -- the free-text fields where a candidate writes
a substantive answer (e.g. "Why do you want to work here?", "Describe your
experience with X"). Exclude logistics/identity fields (name, email, phone,
resume upload, website, LinkedIn, address, yes/no selects, agreements,
demographic self-identification) -- those aren't drafted content. Output
ONLY a JSON object: {"questions": [{"id": "<short_snake_case_id>",
"prompt_text": "<the question, cleaned to a single clear sentence>",
"limit": {"type": "words"|"characters", "target_min": n, "target_max": n}
or null if no limit is stated, "required": true|false}]}."""


def itemize():
    posting = read_text(require_input("job_posting.md"))
    result = call(ITEMIZE_SYSTEM, posting, temperature=0.0)
    write_text(ROOT / "form_itemised.md", result)
    print("Wrote form_itemised.md.")
    print("Review it against the actual form before running --decompose.")


def decompose():
    itemised_path = ROOT / "form_itemised.md"
    if not itemised_path.exists():
        raise SystemExit("form_itemised.md not found -- run without --decompose first.")
    itemised = read_text(itemised_path)
    result = call(DECOMPOSE_SYSTEM, itemised, temperature=0.0)
    questions = parse_json(result)
    write_json(ROOT / "form_questions.json", questions)
    print("Wrote form_questions.json.")


if __name__ == "__main__":
    if "--decompose" in sys.argv:
        decompose()
    else:
        itemize()
