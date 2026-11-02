"""Writes catalog/claims.json: every headline number in the write-up, with the command that recomputes it.

An agent that reviews the submission can run each `recompute` command from the repo root
and compare the output with `value`. tests/test_claims.py does the same check.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "catalog/claims.json"

STATUS = "jq '[.[] | select(.verification == \"{s}\")] | length' catalog/index.json"
CLAIMS = [
    ("actions_total", "Business actions in the catalog, one JSON file each.", "jq length catalog/index.json"),
    *[
        (f"status_{s}", f"Actions with status `{s}`. See AGENT.md for what each status means.", STATUS.format(s=s))
        for s in ("verified", "observed", "gated", "failed", "seen", "documented")
    ],
    (
        "verified_writes",
        "Verified actions that change data. Each one has a read-back that confirmed the change.",
        'jq -s \'[.[] | select(.verification.status == "verified" and .operation_class != "read")] | length\' catalog/actions/*.json',
    ),
    (
        "verified_writes_without_read_back",
        "Verified writes with no read-back. Must be 0.",
        'jq -s \'[.[] | select(.verification.status == "verified" and .operation_class != "read" and .postcondition == null)] | length\' catalog/actions/*.json',
    ),
    (
        "requires_confirmation",
        "Actions that need the user's OK before they run: sends, deletes and writes that nothing can undo.",
        "jq '[.[] | select(.requires_confirmation)] | length' catalog/index.json",
    ),
    (
        "live_api_calls",
        "Calls made to the live Brevo API. Each is one line in the evidence log.",
        "jq -s '[.[] | select(.status != null)] | length' evidence/runs.jsonl",
    ),
    (
        "web_app_actions",
        "Business actions found in the web app walk.",
        "jq .web_app_walk.business_actions catalog/coverage.json",
    ),
    (
        "web_app_catalog_actions",
        "Catalog actions behind the web app actions. One action can serve several buttons.",
        "jq .web_app_walk.catalog_actions catalog/coverage.json",
    ),
    (
        "web_app_actions_with_public_api",
        "Web app actions whose catalog action runs through the public API.",
        "jq .web_app_walk.runs_through_public_api catalog/coverage.json",
    ),
    ("corrections", "Mistakes logged while building the catalog.", "wc -l < docs/corrections.jsonl"),
    (
        "corrections_with_check",
        "Logged mistakes that name the automated check that now catches them.",
        "jq -s '[.[] | select(.now_checked_by != null or .check != null)] | length' docs/corrections.jsonl",
    ),
    (
        "lint_errors",
        "Errors from the catalog lint. Must be 0.",
        "jq '[.[] | select(.severity == \"error\")] | length' catalog/lint.json",
    ),
]


def run(command: str) -> int:
    out = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


AGENT_DOC = ROOT / "AGENT.md"
START, END = "<!-- claims:start -->", "<!-- claims:end -->"


def table(claims: list[dict]) -> str:
    rows = [f"| `{c['id']}` | {c['value']} | {c['meaning']} |" for c in claims]
    return "\n".join([START, "| Claim | Value | Meaning |", "|---|---|---|", *rows, END])


def main() -> None:
    claims = [{"id": i, "value": run(c), "meaning": m, "recompute": c} for i, m, c in CLAIMS]
    OUT.write_text(
        json.dumps({"how_to_check": "Run each recompute command from the repo root.", "claims": claims}, indent=2)
        + "\n"
    )
    text = AGENT_DOC.read_text()
    AGENT_DOC.write_text(text.split(START)[0] + table(claims) + text.split(END)[1])
    print(f"wrote {len(claims)} claims to {OUT.relative_to(ROOT)} and {AGENT_DOC.name}")


if __name__ == "__main__":
    main()
