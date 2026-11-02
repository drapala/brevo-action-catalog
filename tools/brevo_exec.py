"""Execute and verify catalog actions against a live Brevo account.

The executor is the same code an agent would use, so a verified action is
executable by construction. Every call writes one evidence line; the API key
never reaches the evidence.

Usage:
  brevo_exec.py call <action_id> '<json inputs>'
  brevo_exec.py probe-reads            # every read action that needs no ID
  brevo_exec.py scenario <file.yaml>   # create, read back, update, delete flows

A scenario step can carry `known_defect: <text>` when Brevo itself misbehaves. The
failure is still recorded as evidence, so the catalog marks the write action
failed, but it does not stop the run or open a correction.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
import yaml
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog/actions"
ACTIONS = ROOT / "build/openapi_actions"
UI_ACTIONS = ROOT / "sources/ui_actions"
EVIDENCE = ROOT / "evidence/runs.jsonl"
FIXTURE_PREFIX = "zz-catalog-test"


def api_key() -> str:
    key = os.environ.get("BREVO_API_KEY")
    if key:
        return key
    out = subprocess.run(
        ["security", "find-generic-password", "-s", "brevo-api-key", "-w"], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise RuntimeError(
            "No Brevo API key: set BREVO_API_KEY or store it with `security add-generic-password -s brevo-api-key -a brevo -w`"
        )
    return out.stdout.strip()


def load_action(action_id: str) -> dict:
    for folder in (CATALOG, ACTIONS, UI_ACTIONS):
        path = folder / f"{action_id}.json"
        if path.exists():
            return json.loads(path.read_text())
    sys.exit(f"unknown action {action_id}")


def summarize(body) -> object:
    """Keep evidence small: shape and a few values, never whole lists."""
    if isinstance(body, dict):
        out = {}
        for k, v in list(body.items())[:12]:
            if isinstance(v, list):
                out[k] = f"[list of {len(v)}]"
            elif isinstance(v, dict):
                out[k] = "{object}"
            else:
                out[k] = v
        return out
    if isinstance(body, list):
        return f"[list of {len(body)}]"
    return body


def record(entry: dict) -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    entry["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with EVIDENCE.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def input_errors(action: dict, inputs: dict) -> list[str]:
    """Inputs the action does not take, then every place the inputs break its schema."""
    schema = action["inputs"]["schema"]
    unknown = sorted(set(inputs) - set(schema.get("properties") or {}))
    if unknown:
        return [f"unknown inputs {unknown}. This action takes {sorted(schema.get('properties') or {})}"]
    return [describe(e) for e in Draft7Validator(pin_branches(schema)).iter_errors(inputs)]


def describe(error) -> str:
    where = ".".join(map(str, error.path)) or "inputs"
    if error.validator in ("anyOf", "oneOf"):
        needs = [
            " and ".join(b["required"]) for b in error.validator_value if isinstance(b, dict) and b.get("required")
        ]
        if needs:
            exactly = "exactly " if error.validator == "oneOf" else ""
            return f"{where}: needs {exactly}one of: {'; '.join(needs)}"
    return f"{where}: {error.message}"


def pin_branches(node):
    """The spec writes oneOf branches that each name one field but require none, so any object
    matches every branch. Each such branch now requires its field: {"emails": [...]} passes, {} does not."""
    if isinstance(node, dict):
        out = {k: pin_branches(v) for k, v in node.items()}
        for key in ("oneOf", "anyOf"):
            for branch in out.get(key) or []:
                fields = list((branch.get("properties") or {}) if isinstance(branch, dict) else [])
                if len(fields) == 1 and not branch.get("required"):
                    branch["required"] = fields
        return out
    if isinstance(node, list):
        return [pin_branches(v) for v in node]
    return node


def call(
    action_id: str, inputs: dict, client: httpx.Client, run: str = "manual", action: dict | None = None
) -> tuple[int, object]:
    action = action or load_action(action_id)
    route = next(r for r in action["routes"] if r["kind"] == "documented_api")
    url = route["url"]
    query, body = {}, {}
    for name, value in inputs.items():
        loc = route["params"].get(name)
        if loc == "path":
            url = url.replace("{" + name + "}", quote(str(value), safe="@"))
        elif loc == "query":
            query[name] = value
        elif loc == "body" and name == "body":
            body = value
        else:
            body[name] = value
    missing = re.findall(r"\{(\w+)\}", url)
    if missing:
        raise ValueError(f"{action_id}: missing path inputs {missing}")
    try:
        response = client.request(route["method"], url, params=query or None, json=body or None)
    except httpx.TransportError as error:
        record({"run": run, "action": action_id, "method": route["method"], "url": url, "error": repr(error)})
        raise
    try:
        payload = response.json() if response.content else None
    except ValueError:
        payload = response.text[:300]
    record(
        {
            "run": run,
            "action": action_id,
            "method": route["method"],
            "url": url,
            "status": response.status_code,
            "expected": route.get("success_status"),
            "response": summarize(payload),
        }
    )
    return response.status_code, payload


def client() -> httpx.Client:
    return httpx.Client(
        headers={"api-key": api_key(), "accept": "application/json", "content-type": "application/json"},
        timeout=30,
    )


def probe_reads() -> None:
    """Call every read action whose required inputs are all optional or absent."""
    run = f"probe-reads-{int(time.time())}"
    with client() as c:
        for path in sorted(ACTIONS.glob("*.json")):
            action = json.loads(path.read_text())
            if action["operation_class"] != "read":
                continue
            required = action["inputs"]["schema"].get("required", [])
            if required:
                continue
            status, payload = call(action["id"], {}, c, run)
            print(f"{status} {action['id']}")
            time.sleep(0.25)


def render(value, ctx: dict):
    if isinstance(value, str):

        def sub(m):
            cur = ctx
            for part in m.group(1).split("."):
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            return str(cur)

        full = re.fullmatch(r"\$\{([^}]+)\}", value)
        if full:
            cur = ctx
            for part in full.group(1).split("."):
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            return cur
        return re.sub(r"\$\{([^}]+)\}", sub, value)
    if isinstance(value, dict):
        return {k: render(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, ctx) for v in value]
    return value


def lookup(payload, path: str):
    cur = payload
    for part in path.split("."):
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def check(assertion: dict, status: int, payload, ctx: dict) -> tuple[bool, str]:
    if "status" in assertion and status not in (
        assertion["status"] if isinstance(assertion["status"], list) else [assertion["status"]]
    ):
        return False, f"status {status} not in {assertion['status']}"
    for path, expected in (assertion.get("equals") or {}).items():
        cur = lookup(payload, path)
        expected = render(expected, ctx)
        if cur != expected:
            return False, f"{path} = {cur!r}, expected {expected!r}"
    contains = assertion.get("list_contains")
    if contains:
        items = lookup(payload, contains["path"])
        field, want = contains["field"], render(contains["value"], ctx)
        if not isinstance(items, list) or not any(isinstance(i, dict) and i.get(field) == want for i in items):
            return False, f"no item with {field}={want!r} in {contains['path']}"
    for path in assertion.get("present") or []:
        if lookup(payload, path) in (None, ""):
            return False, f"{path} is missing or empty"
    excludes = assertion.get("list_excludes")
    if excludes:
        items = lookup(payload, excludes["path"])
        field, unwanted = excludes["field"], render(excludes["value"], ctx)
        if not isinstance(items, list):
            return False, f"{excludes['path']} is not a list in the response"
        if any(isinstance(i, dict) and i.get(field) == unwanted for i in items):
            return False, f"{excludes['path']} still has an item with {field}={unwanted!r}"
    return True, "ok"


def scenario(file: str) -> int:
    spec = yaml.safe_load(Path(file).read_text())
    run = f"{spec['name']}-{int(time.time())}"
    ctx: dict = {"run": run, "prefix": FIXTURE_PREFIX, "ts": str(int(time.time()))}
    failures = 0
    findings = []
    with client() as c:
        for step in spec["steps"]:
            inputs = render(step.get("inputs") or {}, ctx)
            retry = step.get("retry") or {}
            attempts = 1 + max(0, int(retry.get("times", 0)))
            for attempt in range(1, attempts + 1):
                status, payload = call(step["action"], inputs, c, run)
                ok, why = check(step.get("assert") or {}, status, payload, ctx)
                if ok or attempt == attempts:
                    break
                time.sleep(float(retry.get("every", 2)))
            ctx[step["name"]] = {"status": status, "response": payload}
            record(
                {
                    "run": run,
                    "step": step["name"],
                    "action": step["action"],
                    "verdict": "pass" if ok else "fail",
                    "attempts": attempt,
                    "why": why,
                    "proves": step.get("proves"),
                    "postcondition_of": step.get("postcondition_of"),
                    "note": step.get("note") or step.get("known_defect"),
                }
            )
            label = "PASS" if ok else ("KNOWN" if step.get("known_defect") else "FAIL")
            print(f"{label:5} {step['name']:28} {step['action']} {status} {'' if ok else why}")
            # A known Brevo defect: recorded as evidence, never a ledger entry.
            if not ok and not step.get("known_defect"):
                failures += 1
                findings.append(
                    {
                        "check": f"V-{spec['name']}",
                        "target": step["action"],
                        "severity": "error",
                        "message": f"step {step['name']} ({step['action']}): {why}",
                    }
                )
                if step.get("stop_on_fail", True):
                    break
            time.sleep(step.get("wait", 0.3))
    sys.path.insert(0, str(ROOT / "tools"))
    import corrections

    for change in corrections.sync(findings, "live_verifier", {f"V-{spec['name']}"}):
        print("ledger:", change)
    corrections.render()
    return failures


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "call":
        inputs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        errors = input_errors(load_action(sys.argv[2]), inputs)
        if errors:
            sys.exit("inputs do not match the catalog entry:\n" + "\n".join(errors))
        with client() as c:
            status, payload = call(sys.argv[2], inputs, c)
        print(status, json.dumps(payload, indent=2)[:3000])
    elif cmd == "probe-reads":
        probe_reads()
    elif cmd == "scenario":
        sys.exit(1 if scenario(sys.argv[2]) else 0)
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
