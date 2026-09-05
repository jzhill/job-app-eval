"""Stage 4: External Reference Ingestion.

Reads input/external_resources.md (list of URLs, one per line, optional
trailing note) and files in input/external_refs/, produces a short digest
of each in external_references.md. Optional stage -- writes an (empty)
external_references.md either way, so downstream stages always find it.
"""

import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import INPUT, ROOT, call, write_text

SUMMARIZE_SYSTEM = """Summarize this source in 2-4 sentences: what it's
about and the key facts/claims relevant to a job application. Be concise
and factual, no filler."""


def fetch_url_text(url: str) -> str:
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def read_pdf_text(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_resource_lines():
    resources_path = INPUT / "external_resources.md"
    if not resources_path.exists():
        return []
    lines = []
    for line in resources_path.read_text(encoding="utf-8").splitlines():
        line = line.lstrip("-* ").strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def main():
    entries = []

    for line in parse_resource_lines():
        url = line.split()[0]
        note = line[len(url):].strip(" -")
        print(f"Fetching {url} ...")
        try:
            raw = fetch_url_text(url)
        except Exception as exc:
            print(f"  skipped ({exc})")
            continue
        summary = call(SUMMARIZE_SYSTEM, raw[:20000], temperature=0.0)
        entries.append((url, url, summary, note))

    refs_dir = INPUT / "external_refs"
    if refs_dir.exists():
        for path in sorted(refs_dir.iterdir()):
            if path.suffix.lower() != ".pdf":
                continue
            print(f"Reading {path.name} ...")
            raw = read_pdf_text(path)
            summary = call(SUMMARIZE_SYSTEM, raw[:20000], temperature=0.0)
            entries.append((path.name, path.name, summary, ""))

    lines = ["# External References\n"]
    for title, source, summary, note in entries:
        lines.append(f"## {title}")
        lines.append(f"Source: {source}")
        lines.append(f"Summary: {summary}")
        if note:
            lines.append(f"Why flagged: {note}")
        lines.append("")

    write_text(ROOT / "external_references.md", "\n".join(lines))
    print(f"Wrote external_references.md ({len(entries)} entries).")


if __name__ == "__main__":
    main()
