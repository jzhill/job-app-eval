"""Stage 8: Voice Profiling.

One-time distillation from corrected source text only -- never raw
dictated/transcribed originals, since transcription artifacts (dropped
words, subject-verb agreement) risk being encoded as "voice". Reads
input/past_drafts/*.md. Not regenerated per round; re-run by hand only
if Jeremy supplies substantial new source material.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import INPUT, ROOT, call, write_text

SYSTEM = """Analyze the writing samples below and describe the author's
voice as a set of named characteristics an editor could apply -- not
example sentences to imitate. Cover: sentence rhythm, signature moves,
paragraph-opening patterns, register, and things to avoid (hedging,
exclamation points, rhetorical questions, generic AI-assistant phrasing).
Output markdown, a "# Voice Profile" heading followed by bullet points."""


def main():
    drafts_dir = INPUT / "past_drafts"
    if not drafts_dir.exists() or not any(drafts_dir.glob("*.md")):
        print("No corrected source text found in input/past_drafts/*.md -- skipping.")
        print("Voice profiling only runs on Jeremy's own corrected writing samples.")
        return

    samples = []
    for path in sorted(drafts_dir.glob("*.md")):
        samples.append(f"## {path.name}\n{path.read_text(encoding='utf-8')}")

    result = call(SYSTEM, "\n\n".join(samples), temperature=0.0)
    write_text(ROOT / "voice_profile.md", result)
    print("Wrote voice_profile.md.")


if __name__ == "__main__":
    main()
