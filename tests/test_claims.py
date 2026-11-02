"""Every number in catalog/claims.json must match its recompute command, so the write-up cannot drift from the data."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("jq") is None, reason="the recompute commands use jq")
def test_every_claim_matches_its_recompute_command():
    claims = json.loads((ROOT / "catalog/claims.json").read_text())["claims"]
    for claim in claims:
        out = subprocess.run(claim["recompute"], shell=True, cwd=ROOT, capture_output=True, text=True, check=True)
        assert int(out.stdout.strip()) == claim["value"], claim["id"]
    by_id = {c["id"]: c["value"] for c in claims}
    assert by_id["verified_writes_without_read_back"] == 0 and by_id["lint_errors"] == 0
