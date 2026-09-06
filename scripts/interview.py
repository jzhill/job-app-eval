"""Stage 6: Reflective Interview.

This script does not conduct the interview -- Claude Code has no voice
interface, and there's no session handoff to claude.ai/Gemini/ChatGPT's
voice-mode apps. Instead:

  python scripts/interview.py --brief
      writes interview_brief.md: a self-contained prompt to paste into a
      voice-mode app and have the actual conversation there.

  python scripts/interview.py --ingest <path to pasted-back transcript>
      normalizes whatever the external agent returned into
      interview_report.md (organized report + verbatim-quotes section).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import OUTPUT, call, read_cv_text, read_json, read_text, write_text

BRIEF_TEMPLATE = """You are conducting a reflective interview with a job
candidate, out loud, in conversation (they may be driving or walking, so
keep your turns spoken and natural, not a wall of text).

Your goal is NOT a rote Q&A pass through missing requirements. It's a
curious, thoughtful exchange to draw out their real motivations, ideas,
and intentions in relation to this specific role -- the kind of material
that only surfaces through dialogue, not a written form. Ask genuinely
interested follow-up questions. Let the conversation breathe.

## The job

{jd_components}

## What they've already covered in writing (don't re-ask this; probe
deeper or explore what's NOT here)

{coverage_gaps}

## Their CV, for context

{cv}

When the conversation feels complete, produce a written report with two
parts:
1. An organized, annotated write-up of what came out of the conversation,
   grouped by theme.
2. A separate section of verbatim quotes or passages that were
   particularly compelling, worth reusing directly.

Start the conversation now with a warm, specific opening question.
"""

INGEST_SYSTEM = """You are given a raw transcript or summary from a
reflective interview conversation. Normalize it into two markdown
sections:
## Interview Report
An organized, annotated write-up grouped by theme (not a raw transcript).
## Compelling Quotes
Verbatim quotes or passages worth reusing directly in application drafts.
Output only the markdown, no preamble."""


def write_brief():
    components = read_json(OUTPUT / "jd_components.json")
    tagged_path = OUTPUT / "tagged_context.json"
    gaps = read_json(tagged_path).get("coverage_gaps", []) if tagged_path.exists() else []
    cv = read_cv_text()

    brief = BRIEF_TEMPLATE.format(
        jd_components=components,
        coverage_gaps=gaps or "(no specific gaps flagged)",
        cv=cv,
    )
    write_text(OUTPUT / "interview_brief.md", brief)
    print("Wrote output/interview_brief.md.")
    print("Paste this into Claude/Gemini/ChatGPT's voice mode and have the conversation.")
    print("Then run: python scripts/interview.py --ingest <path to what it gave you back>")


def ingest(transcript_path: str):
    transcript = read_text(Path(transcript_path))
    result = call(INGEST_SYSTEM, transcript, temperature=0.0)
    write_text(OUTPUT / "interview_report.md", result)
    print("Wrote output/interview_report.md.")


if __name__ == "__main__":
    if "--ingest" in sys.argv:
        idx = sys.argv.index("--ingest")
        ingest(sys.argv[idx + 1])
    else:
        write_brief()
