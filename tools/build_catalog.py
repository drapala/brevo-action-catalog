"""Assemble the final catalog.

Inputs, in order of authority (later wins):
  1. build/openapi_actions/   drafts generated from the official spec
  2. sources/ui_actions/      actions found by walking the web app
  3. catalog/curation.yaml    reviewed corrections, each with a reason
  4. evidence/runs.jsonl      live results, which set verification status

Outputs: catalog/actions/*.json, catalog/index.json, catalog/coverage.json
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "build/openapi_actions"
UI = ROOT / "sources/ui_actions"
CURATION = ROOT / "catalog/curation.yaml"
EVIDENCE = ROOT / "evidence/runs.jsonl"
OUT = ROOT / "catalog/actions"
SCHEMA = ROOT / "catalog/schema/business_action.schema.json"

GATED_HINTS = (
    "not enabled",
    "upgrade",
    "plan",
    "permission",
    "not activated",
    "not allowed",
    "subscribe",
    "access denied",
)


def deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_actions() -> dict[str, dict]:
    actions = {}
    for folder in (DRAFTS, UI):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            action = json.loads(path.read_text())
            if action["id"] in actions:
                # A UI action with the same id as a spec action adds routes to it.
                merged = actions[action["id"]]
                merged["routes"] += [r for r in action["routes"] if r not in merged["routes"]]
                merged["sources"] += action["sources"]
            else:
                actions[action["id"]] = action
    return actions


def apply_curation(actions: dict[str, dict]) -> int:
    if not CURATION.exists():
        return 0
    patches = yaml.safe_load(CURATION.read_text()) or {}
    for action_id, entry in patches.items():
        if action_id not in actions:
            raise KeyError(f"curation targets unknown action {action_id}")
        patch = {k: v for k, v in entry.items() if k != "why"}
        if not entry.get("why"):
            raise ValueError(f"curation for {action_id} has no 'why'")
        actions[action_id] = deep_merge(actions[action_id], patch)
    return len(patches)


def apply_evidence(actions: dict[str, dict]) -> None:
    if not EVIDENCE.exists():
        return
    calls: dict[str, list[dict]] = defaultdict(list)
    verdicts: dict[str, list[dict]] = defaultdict(list)
    for line in EVIDENCE.read_text().splitlines():
        entry = json.loads(line)
        if "verdict" in entry:
            verdicts[entry["action"]].append(entry)
        elif "status" in entry:
            calls[entry["action"]].append(entry)
    for action_id, action in actions.items():
        v = action["verification"]
        passed = [e for e in verdicts.get(action_id, []) if e["verdict"] == "pass"]
        failed = [e for e in verdicts.get(action_id, []) if e["verdict"] == "fail"]
        probes = [c for c in calls.get(action_id, []) if c["run"].startswith("probe-reads")]
        if passed:
            v.update(
                status="verified",
                route_kind="documented_api",
                checked_at=passed[-1]["at"],
                evidence=f"evidence/runs.jsonl#run={passed[-1]['run']}",
            )
            action["availability"]["free_plan"] = "available"
        elif probes:
            last = probes[-1]
            message = json.dumps(last.get("response"), ensure_ascii=False)
            if last["status"] in (last.get("expected") or [200]):
                v.update(
                    status="verified",
                    route_kind="documented_api",
                    checked_at=last["at"],
                    evidence=f"evidence/runs.jsonl#run={last['run']}",
                    notes="read probe returned the documented success status",
                )
                action["availability"]["free_plan"] = "available"
            elif last["status"] in (402, 403) or any(h in message.lower() for h in GATED_HINTS):
                v.update(
                    status="gated",
                    route_kind="documented_api",
                    checked_at=last["at"],
                    evidence=f"evidence/runs.jsonl#run={last['run']}",
                    notes=f"HTTP {last['status']}: {message[:200]}",
                )
                action["availability"]["free_plan"] = "gated"
                action["availability"]["evidence"] = f"HTTP {last['status']} on the free plan"
            else:
                v.update(
                    status="failed",
                    route_kind="documented_api",
                    checked_at=last["at"],
                    evidence=f"evidence/runs.jsonl#run={last['run']}",
                    notes=f"HTTP {last['status']}: {message[:200]}",
                )
        elif failed:
            last = failed[-1]
            v.update(
                status="failed",
                route_kind="documented_api",
                checked_at=last["at"],
                evidence=f"evidence/runs.jsonl#run={last['run']}",
                notes=last.get("why", ""),
            )


def main() -> None:
    actions = load_actions()
    n_curated = apply_curation(actions)
    apply_evidence(actions)

    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    index = []
    for action in sorted(actions.values(), key=lambda a: a["id"]):
        errors = list(validator.iter_errors(action))
        if errors:
            raise ValueError(f"{action['id']}: {errors[0].message}")
        (OUT / f"{action['id']}.json").write_text(json.dumps(action, indent=2, ensure_ascii=False) + "\n")
        index.append(
            {
                "id": action["id"],
                "label": action["label"],
                "area": action["area"],
                "entity": action["entity"],
                "operation_class": action["operation_class"],
                "route_kinds": sorted({r["kind"] for r in action["routes"]}),
                "verification": action["verification"]["status"],
                "free_plan": action["availability"]["free_plan"],
                "requires_confirmation": action["side_effects"]["requires_confirmation"],
            }
        )
    (ROOT / "catalog/index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

    by_status = Counter(i["verification"] for i in index)
    by_route = Counter(k for i in index for k in i["route_kinds"])
    ui_only = [i["id"] for i in index if i["route_kinds"] == ["ui_path"] or "documented_api" not in i["route_kinds"]]
    areas = defaultdict(Counter)
    for i in index:
        areas[i["area"]][i["verification"]] += 1
    coverage = {
        "total_actions": len(index),
        "by_verification": dict(by_status),
        "by_route_kind": dict(by_route),
        "without_public_api": len(ui_only),
        "curated_entries": n_curated,
        "by_area": {a: dict(c) for a, c in sorted(areas.items())},
    }
    (ROOT / "catalog/coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    print(json.dumps({k: v for k, v in coverage.items() if k != "by_area"}, indent=2))


if __name__ == "__main__":
    main()
