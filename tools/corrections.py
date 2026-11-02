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
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs/corrections.jsonl"
AI_LOG = ROOT / "docs/AI_LOG.md"
START = "<!-- corrections:start -->"
END = "<!-- corrections:end -->"

ERRED_BY = ["ai_agent", "ai_generated_code", "brevo_platform", "human", "tooling"]
CAUGHT_BY = ["human", "catalog_lint", "live_verifier", "reviewer_agent", "agent_self_check", "brevo_platform"]
AUTOMATED = {"catalog_lint", "live_verifier", "reviewer_agent"}


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
    auto = sum(1 for e in entries if e["caught_by"] in AUTOMATED)
    by_agent = sum(1 for e in entries if e["caught_by"] == "agent_self_check")
    by_human = sum(1 for e in entries if e["caught_by"] == "human")
    by_platform = sum(1 for e in entries if e["caught_by"] == "brevo_platform")
    open_n = sum(1 for e in entries if e.get("status", "fixed") == "open")
    lines = [
        START,
        f"{len(entries)} corrections: {auto} caught by automated checks, {by_agent} by the agent during the session, "
        f"{by_human} by a human, {by_platform} by Brevo itself. Open: {open_n}.",
        "",
        "| ID | Phase | What went wrong | Caught by | Status | Fix |",
        "|---|---|---|---|---|---|",
    ]
    for e in entries:
        what = e["what"] + (f" Evidence: `{e['evidence']}`." if e.get("evidence") else "")
        status = e.get("status", "fixed")
        if e.get("now_checked_by"):
            status += f", now caught by check {e['now_checked_by']}"
        lines.append(f"| {e['id']} | {e['phase']} | {what} | {e['caught_by'].replace('_', ' ')} | {status} | {e['fix']} |")
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


def save(entries: list[dict]) -> None:
    LEDGER.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))


def sync(findings: list[dict], source: str, checks: set[str]) -> list[str]:
    """Open one entry per failing check, update it while it fails, close it when it passes.

    Only the checks in `checks` are judged, so a partial run never closes an
    entry it did not re-examine.
    """
    entries = load()
    errors: dict[str, list[dict]] = {}
    for f in findings:
        if f["severity"] == "error":
            errors.setdefault(f["check"], []).append(f)
    changed = []
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    for check in sorted(checks):
        open_entry = next((e for e in entries if e.get("check") == check and e.get("status") == "open"), None)
        found = errors.get(check, [])
        if found:
            examples = "; ".join(f["message"] for f in found[:3])
            what = f"Check {check} failed on {len(found)} entries, for example: {examples}."
            if open_entry:
                if open_entry["what"] != what:
                    open_entry.update(what=what, targets=[f["target"] for f in found])
                    changed.append(f"updated {open_entry['id']}")
            else:
                entry = {
                    "id": f"C{len(entries) + 1:03d}", "at": now, "phase": "automated check",
                    "erred_by": "ai_generated_code", "what": what, "caught_by": source,
                    "fix": "open: the agent fixes the cause and the same check closes this entry",
                    "evidence": None, "commit": head(), "status": "open", "check": check,
                    "targets": [f["target"] for f in found],
                }
                entries.append(entry)
                changed.append(f"opened {entry['id']} ({check}, {len(found)} findings)")
        elif open_entry:
            open_entry.update(status="fixed", fixed_at=now, fixed_commit=head())
            if open_entry["fix"].startswith("open:"):
                open_entry["fix"] = f"Check {check} passes again at commit {head()}."
            changed.append(f"closed {open_entry['id']} ({check})")
    save(entries)
    return changed


def annotate(entry_id: str, fix: str) -> None:
    entries = load()
    for e in entries:
        if e["id"] == entry_id:
            e["fix"] = fix
    save(entries)


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
    n = sub.add_parser("annotate")
    n.add_argument("entry_id")
    n.add_argument("--fix", required=True)
    args = parser.parse_args()
    if args.cmd == "add":
        add(args)
    elif args.cmd == "render":
        render()
    elif args.cmd == "annotate":
        annotate(args.entry_id, args.fix)
        render()
    else:
        raise SystemExit(check())


if __name__ == "__main__":
    main()
