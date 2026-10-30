"""Checks to run before sending the submission.

1. No credential in any tracked file (Brevo keys, bearer tokens, cookies).
2. Every action in the catalog validates against the schema.
3. The public repository URL answers 200 to a client that is not logged in.

Usage: presubmit_check.py [repo_url]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import httpx
import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [
    re.compile(r"xkeysib-[a-f0-9]{20,}"),
    re.compile(r"xsmtpsib-[a-f0-9]{20,}"),
    re.compile(r"(?i)api-key:\s*[a-z0-9-]{20,}"),
    re.compile(r"(?i)authorization:\s*bearer\s+[a-z0-9._-]{20,}"),
    re.compile(r"(?i)set-cookie|\bsessionid=|\bcsrftoken="),
]


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / line for line in out.stdout.splitlines() if line]


def check_secrets() -> list[str]:
    hits = []
    for path in tracked_files():
        if path.suffix in {".png", ".jpg", ".pdf", ".mp4"} or not path.exists():
            continue
        text = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)}: matches {pattern.pattern}")
    return hits


def check_schema() -> list[str]:
    validator = jsonschema.Draft202012Validator(
        json.loads((ROOT / "catalog/schema/business_action.schema.json").read_text())
    )
    errors = []
    for path in sorted((ROOT / "catalog/actions").glob("*.json")):
        for err in validator.iter_errors(json.loads(path.read_text())):
            errors.append(f"{path.name}: {err.message[:120]}")
            break
    return errors


def check_public(url: str) -> list[str]:
    status = httpx.get(url, follow_redirects=True, timeout=20).status_code
    return [] if status == 200 else [f"{url} answered {status} to a logged-out client"]


def main() -> int:
    problems = check_secrets() + check_schema()
    if len(sys.argv) > 1:
        problems += check_public(sys.argv[1])
    for problem in problems:
        print("FAIL", problem)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
