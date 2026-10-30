"""Ledger of every correction made while building the catalog.

Each line of docs/corrections.jsonl records one thing that went wrong, who or
what caught it, and the fix. `render` rewrites the table in docs/AI_LOG.md, so
the write-up always matches the ledger.

Usage:
  corrections.py add --phase P --erred-by WHO --what TEXT --caught-by WHO --fix TEXT [--evidence REF]
  corrections.py render
  corrections.py check     # exit 1 if docs/AI_LOG.md does not match the ledger
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs/corrections.jsonl"
AI_LOG = ROOT / "docs/AI_LOG.md"
START = "<!-- corrections:start -->"
END = "<!-- corrections:end -->"

ERRED_BY = ["ai_agent", "ai_generated_code", "brevo_platform", "human", "tooling"]
CAUGHT_BY = ["human", "live_verifier", "reviewer_agent", "agent_self_check", "brevo_platform"]


def head() -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() or "uncommitted"


def add(args: argparse.Namespace) -> None:
    entries = load()
    entry = {
        "id": f"C{len(entries) + 1:03d}",
        "at": args.at or datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "phase": args.phase,
        "erred_by": args.erred_by,
        "what": args.what,
        "caught_by": args.caught_by,
        "fix": args.fix,
        "evidence": args.evidence,
        "commit": head(),
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(entry["id"])


def load() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def block() -> str:
    entries = load()
    caught = Counter(e["caught_by"] for e in entries)
    erred = Counter(e["erred_by"] for e in entries)
    lines = [
        START,
        f"{len(entries)} corrections. Caught by: "
        + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in caught.most_common())
        + ". Source of the error: "
        + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in erred.most_common())
        + ".",
        "",
        "| ID | Phase | What went wrong | Caught by | Fix |",
        "|---|---|---|---|---|",
    ]
    for e in entries:
        what = e["what"] + (f" Evidence: `{e['evidence']}`." if e.get("evidence") else "")
        lines.append(f"| {e['id']} | {e['phase']} | {what} | {e['caught_by'].replace('_', ' ')} | {e['fix']} |")
    lines.append(END)
    return "\n".join(lines)


def render() -> None:
    text = AI_LOG.read_text()
    new = block()
    if START in text:
        text = text.split(START)[0] + new + text.split(END)[1]
    else:
        text = text.rstrip() + "\n\n## Corrections ledger\n\n" + new + "\n"
    AI_LOG.write_text(text)
    print(f"rendered {len(load())} entries into {AI_LOG.relative_to(ROOT)}")


def check() -> int:
    text = AI_LOG.read_text()
    current = START + text.split(START)[1].split(END)[0] + END if START in text else ""
    if current != block():
        print("docs/AI_LOG.md is out of date with docs/corrections.jsonl: run corrections.py render")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--phase", required=True)
    a.add_argument("--erred-by", required=True, choices=ERRED_BY)
    a.add_argument("--what", required=True)
    a.add_argument("--caught-by", required=True, choices=CAUGHT_BY)
    a.add_argument("--fix", required=True)
    a.add_argument("--evidence")
    a.add_argument("--at")
    sub.add_parser("render")
    sub.add_parser("check")
    args = parser.parse_args()
    if args.cmd == "add":
        add(args)
    elif args.cmd == "render":
        render()
    else:
        raise SystemExit(check())


if __name__ == "__main__":
    main()
