"""Shared helpers for the job-app-eval pipeline scripts."""

import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"

load_dotenv(ROOT / ".env")

DEFAULT_MODEL = "claude-sonnet-5"


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Get a key from console.anthropic.com "
            "and export it before running pipeline scripts."
        )
    return anthropic.Anthropic(api_key=api_key)


def call(system: str, user: str, model: str = DEFAULT_MODEL,
         effort: str | None = None, max_tokens: int = 4096) -> str:
    """effort: None (SDK default) or one of "low"/"medium"/"high"/"xhigh"/"max".
    The Messages API has no temperature/top_p/top_k/seed parameter -- effort
    (via output_config) is the only sampling-behavior knob it now exposes."""
    client = get_client()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if effort:
        kwargs["output_config"] = {"effort": effort}
    message = client.messages.create(**kwargs)
    return "".join(block.text for block in message.content if block.type == "text")


def parse_json(text: str):
    """Extract a JSON object/array from a model response, tolerating ```json fences."""
    match = re.search(r"```(?:json)?\s*([\[{].*[\]}])\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else text.strip()
    return json.loads(candidate)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path):
    return json.loads(read_text(path))


def require_input(name: str) -> Path:
    path = INPUT / name
    if not path.exists():
        raise SystemExit(f"Required input missing: input/{name}")
    return path


def find_cv_path() -> Path:
    for ext in (".docx", ".pdf", ".md", ".txt"):
        candidate = INPUT / f"current_cv{ext}"
        if candidate.exists():
            return candidate
    raise SystemExit("Required input missing: input/current_cv.{docx,pdf,md}")


def read_cv_text() -> str:
    path = find_cv_path()
    if path.suffix == ".docx":
        import docx
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    if path.suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return read_text(path)


def gen_dir(base: str, gen: int) -> Path:
    return OUTPUT / base / f"gen{gen}"
