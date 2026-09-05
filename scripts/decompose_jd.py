"""Stage 1: JD Decomposition.

Default: itemize input/job_posting.md -> jd_itemised.md, then stop.
Review jd_itemised.md against the actual posting yourself before continuing.

--decompose: read the (reviewed) jd_itemised.md -> jd_components.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, call, parse_json, read_text, require_input, write_json, write_text

ITEMIZE_SYSTEM = """You itemize a job posting into a numbered list, verbatim.
Break the text into a discrete, numbered list of items -- every distinct
requirement, responsibility, sentence, or bullet gets its own item, grouped
under whatever section headers the source text itself used. Quote each item
exactly as written; do not paraphrase, summarize, compress, or drop anything,
including sentences you think are boilerplate -- if something is generic
boilerplate (e.g. a DEI statement or scam warning), still summarize it as its
own item and label it as boilerplate, don't just omit it. Output markdown:
a top-level heading, then "## Section: <name>" headings with numbered items
underneath, numbered continuously across the whole document."""

DECOMPOSE_SYSTEM = """You sort an itemised job posting into four categories:
required_qualifications, preferred_qualifications, core_responsibilities,
mission_signals (the company's stated mission/values/culture, not candidate
requirements). Salary, logistics, visa policy, and legal boilerplate belong
in none of these categories and should be omitted. Output ONLY a JSON object
with exactly those four keys, each a list of {"id": "<short_snake_case_id>",
"text": "<the item's text, cleaned to a single clear sentence>"}."""


def itemize():
    posting = read_text(require_input("job_posting.md"))
    result = call(ITEMIZE_SYSTEM, posting, temperature=0.0)
    write_text(ROOT / "jd_itemised.md", result)
    print("Wrote jd_itemised.md.")
    print("Review it against the actual posting before running --decompose.")


def decompose():
    itemised_path = ROOT / "jd_itemised.md"
    if not itemised_path.exists():
        raise SystemExit("jd_itemised.md not found -- run without --decompose first.")
    itemised = read_text(itemised_path)
    result = call(DECOMPOSE_SYSTEM, itemised, temperature=0.0)
    components = parse_json(result)
    write_json(ROOT / "jd_components.json", components)
    print("Wrote jd_components.json. Review and hand-edit before proceeding --")
    print("a wrong or sloppy decomposition poisons every downstream score.")


if __name__ == "__main__":
    if "--decompose" in sys.argv:
        decompose()
    else:
        itemize()
