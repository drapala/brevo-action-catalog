"""Assemble the final catalog.

Inputs, in order of authority (later wins):
  1. build/openapi_actions/   drafts generated from the official spec
  2. sources/ui_actions/      actions found by walking the web app
  3. sources/ui/ui_map.yaml   every action seen in the web app, joined to the catalog
  4. catalog/curation.yaml    reviewed corrections, each with a reason
  5. evidence/runs.jsonl      live results, which set verification status

Outputs: catalog/actions/*.json, catalog/index.json, catalog/coverage.json
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

import jsonschema
import yaml

import catalog_lint
import corrections
import make_claims

ROOT = Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "build/openapi_actions"
UI = ROOT / "sources/ui_actions"
UI_MAP = ROOT / "sources/ui/ui_map.yaml"
CURATION = ROOT / "catalog/curation.yaml"
EVIDENCE = ROOT / "evidence/runs.jsonl"
SCENARIOS = ROOT / "scenarios"
OUT = ROOT / "catalog/actions"
SCHEMA = ROOT / "catalog/schema/business_action.schema.json"

SETUP_HINTS = ("not activated", "not yet activated", "not enabled", "feature_inactive", "request activation")
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


def seen_action(line: dict, walk: dict) -> dict:
    new = line["new"]
    writes = new["operation_class"] != "read"
    return {
        "id": new["id"],
        "product": "brevo",
        "area": line["area"],
        "entity": new["entity"],
        "operation_class": new["operation_class"],
        "label": line["ui"],
        "description": new["description"],
        "inputs": {"schema": {"type": "object", "properties": {}}, "entity_refs": [], "credential_ref": "brevo_web_session"},
        "outputs": {"produces_entity": None},
        "routes": [{"kind": "ui_path", "ui_steps": line["steps"]}],
        "preconditions": [],
        "postcondition": None,
        "side_effects": {
            "reversible": new.get("reversible", not writes),
            "undo_with": None,
            "external_effect": new.get("external_effect", "none"),
            "idempotent": None,
            "requires_confirmation": new.get("requires_confirmation", writes),
        },
        "availability": {"free_plan": line.get("free_plan", "available"), "requires": line.get("requires", [])},
        "verification": {
            "status": line.get("status", "seen"),
            "route_kind": "ui_path",
            "checked_at": walk["walked_at"],
            "evidence": line.get("evidence", walk["evidence"]),
            "notes": "The free plan shows an upgrade or setup screen instead."
            if line.get("status") == "gated"
            else "Seen in the web app and not run, so the inputs and the exact effect are not known.",
        },
        "sources": [{"kind": "ui_walk", "ref": line.get("source") or f"sources/ui/ui_map.yaml ({line['area']}: {line['ui']})"}],
    }


def apply_ui_map(actions: dict[str, dict]) -> dict:
    """Join every action seen in the web app to the catalog, and return the walk.

    A line with catalog_id adds its UI steps to that action as a ui_path route.
    A line with new becomes a `seen` action. A line with kind view only changes
    what the screen shows, so it is listed but is not a business action. A line
    with status gated marks its catalog action gated when nothing ran it.
    """
    if not UI_MAP.exists():
        return {}
    walk = yaml.safe_load(UI_MAP.read_text())
    lines = [line for line in walk["actions"] if line.get("kind") != "view"]
    for line in lines:
        if line.get("new"):
            if line["new"]["id"] in actions:
                raise ValueError(f"ui_map adds {line['new']['id']}, which the catalog already has")
            actions[line["new"]["id"]] = seen_action(line, walk)
    for line in lines:
        target = actions[line.get("catalog_id") or line["new"]["id"]]
        route = {"kind": "ui_path", "ui_steps": line["steps"]}
        if route not in target["routes"]:
            target["routes"].append(route)
        if line.get("catalog_id") and line.get("status") == "gated" and target["verification"]["status"] == "documented":
            target["verification"].update(status="gated", route_kind="ui_path", checked_at=walk["walked_at"],
                                          evidence=walk["evidence"], notes="The free plan shows an upgrade screen instead.")
            target["availability"]["free_plan"] = "gated"
    return walk


def walk_stats(actions: dict[str, dict], walk: dict) -> dict:
    """Count the web app actions by the route their catalog action has once evidence is applied."""
    if not walk:
        return {}
    lines = [line for line in walk["actions"] if line.get("kind") != "view"]
    added = {line["new"]["id"] for line in lines if line.get("new")}
    targets = {line.get("catalog_id") or line["new"]["id"] for line in lines}
    # One catalog action can serve several buttons: Rename and Move both call update_list.
    stats = Counter(
        view_only=len(walk["actions"]) - len(lines), business_actions=len(lines), catalog_actions=len(targets)
    )
    for line in lines:
        target = actions[line.get("catalog_id") or line["new"]["id"]]
        stats["added_by_walk" if target["id"] in added else "in_catalog_before_walk"] += 1
        kinds = {r["kind"] for r in target["routes"]}
        if target["verification"]["status"] == "gated":
            stats["blocked_on_free_plan"] += 1
        elif "documented_api" in kinds:
            stats["runs_through_public_api"] += 1
        elif "undocumented_api" in kinds:
            stats["internal_endpoint_browser_only"] += 1
        else:
            stats["ui_steps_only"] += 1
    return dict(stats)


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


def scenario_steps() -> dict[tuple[str, str], dict]:
    steps = {}
    for path in sorted(SCENARIOS.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text())
        for step in spec["steps"]:
            steps[(spec["name"], step["name"])] = step
    return steps


def describe_check(assertion: dict) -> str:
    """The read-back check of a scenario step, in words an agent can act on."""
    parts = []
    for path, value in (assertion.get("equals") or {}).items():
        if isinstance(value, str) and "${" in value:
            parts.append(f"`{path}` equals the value that was sent")
        else:
            parts.append(f"`{path}` equals {json.dumps(value)}")
    if assertion.get("list_contains"):
        c = assertion["list_contains"]
        parts.append(f"`{c['path']}` holds an item whose `{c['field']}` is the one that was sent")
    if assertion.get("list_excludes"):
        c = assertion["list_excludes"]
        parts.append(f"`{c['path']}` no longer holds an item whose `{c['field']}` is the one that was sent")
    if not parts and assertion.get("status"):
        parts.append(f"the read returns HTTP {assertion['status']}")
    return "; ".join(parts)


def step_of(entry: dict, steps: dict[tuple[str, str], dict]) -> dict:
    return steps.get((entry["run"].rsplit("-", 1)[0], entry.get("step", "")), {})


def apply_evidence(actions: dict[str, dict]) -> None:
    if not EVIDENCE.exists():
        return
    calls: dict[str, list[dict]] = defaultdict(list)
    verdicts: dict[str, list[dict]] = defaultdict(list)
    postconditions: dict[str, list[dict]] = defaultdict(list)
    steps = scenario_steps()
    for line in EVIDENCE.read_text().splitlines():
        entry = json.loads(line)
        if "verdict" in entry:
            verdicts[entry["action"]].append(entry)
            if entry.get("postcondition_of"):
                postconditions[entry["postcondition_of"]].append(entry)
        elif "status" in entry:
            calls[entry["action"]].append(entry)
    for action_id, action in actions.items():
        v = action["verification"]
        # A failed read-back judges the write it checks, not the read that ran it.
        own = [e for e in verdicts.get(action_id, []) if e["verdict"] == "pass" or not e.get("postcondition_of")]
        passed = [e for e in own if e["verdict"] == "pass"]
        failed = [e for e in own if e["verdict"] == "fail"]
        probes = [c for c in calls.get(action_id, []) if c["run"].startswith("probe-reads")]
        gates = [c for c in calls.get(action_id, []) if c["run"].startswith("probe-gates")]
        checks = postconditions.get(action_id, [])
        good = [c for c in checks if c["verdict"] == "pass"]
        if good and not action.get("postcondition"):
            action["postcondition"] = {
                "check_with": good[-1]["action"],
                "assert": describe_check(step_of(good[-1], steps).get("assert") or {}) or good[-1].get("proves", ""),
            }
        if checks and checks[-1]["verdict"] == "fail":
            last = checks[-1]
            v.update(
                status="failed",
                route_kind="documented_api",
                checked_at=last["at"],
                evidence=f"evidence/runs.jsonl#run={last['run']}",
                notes=f"The call returns success, but the read-back check failed: {last.get('note') or last.get('why', '')}",
            )
            action["availability"]["free_plan"] = "available"
            continue
        if own and own[-1]["verdict"] == "fail":
            last = own[-1]
            v.update(
                status="failed",
                route_kind="documented_api",
                checked_at=last["at"],
                evidence=f"evidence/runs.jsonl#run={last['run']}",
                notes=last.get("why", ""),
            )
            continue
        if passed and action["operation_class"] != "read" and not good:
            v.update(
                checked_at=passed[-1]["at"],
                evidence=f"evidence/runs.jsonl#run={passed[-1]['run']}",
                notes="The call returned success, but no read-back has checked the effect yet.",
            )
            continue
        if passed:
            v.update(
                status="verified",
                route_kind="documented_api",
                checked_at=passed[-1]["at"],
                evidence=f"evidence/runs.jsonl#run={passed[-1]['run']}",
            )
            action["availability"]["free_plan"] = "available"
            notes = [passed[-1]["note"]] if passed[-1].get("note") else []
            route = next(r for r in action["routes"] if r["kind"] == "documented_api")
            live = sorted({c["status"] for c in calls.get(action_id, []) if 200 <= c["status"] < 300})
            spec = route.get("success_status") or [200]
            if live and not set(live) <= set(spec):
                route["success_status"] = live
            if live and not set(live) <= set(spec) and not any("spec documents" in n for n in notes):
                notes.append(f"the spec documents HTTP {spec}, the live API returns {live}")
            # Keep the bare-call error: an agent without setup hits it too.
            if probes and probes[-1]["status"] not in (probes[-1].get("expected") or [200]):
                bare = probes[-1]
                message = json.dumps(bare.get("response"), ensure_ascii=False)
                notes.append(f"a call with no inputs, made before any test data existed, returned HTTP {bare['status']}: {message[:200]}")
            if notes:
                v["notes"] = " ".join(n[0].upper() + n[1:].rstrip(".") + "." for n in notes)
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
        elif gates:
            last = gates[-1]
            message = json.dumps(last.get("response"), ensure_ascii=False)
            refused = last["status"] in (401, 402, 403) and '"bad_request"' not in message
            if refused or any(h in message.lower() for h in GATED_HINTS):
                v.update(
                    status="gated",
                    route_kind="documented_api",
                    checked_at=last["at"],
                    evidence=f"evidence/runs.jsonl#run={last['run']}",
                    notes=f"HTTP {last['status']} to a call with inputs that cannot succeed: {message[:200]}",
                )
                if any(h in message.lower() for h in SETUP_HINTS):
                    action["availability"]["free_plan"] = "limited"
                    action["availability"]["requires"] = ["turn this feature on in the account first"]
                    action["availability"]["evidence"] = f"HTTP {last['status']}: the feature is not turned on"
                else:
                    action["availability"]["free_plan"] = "gated"
                    action["availability"]["evidence"] = f"HTTP {last['status']} on the free plan"
            else:
                v["notes"] = (
                    f"Not run with real inputs. A call with inputs that cannot succeed returned HTTP {last['status']} "
                    f"({message[:160]}). This answer does not show whether the free plan allows the action. "
                    f"Evidence: evidence/runs.jsonl#run={last['run']}."
                )

def main() -> None:
    actions = load_actions()
    walk = apply_ui_map(actions)
    n_curated = apply_curation(actions)
    apply_evidence(actions)
    ui_walk = walk_stats(actions, walk)

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
    ui_only = [i["id"] for i in index if "documented_api" not in i["route_kinds"]]
    areas = defaultdict(Counter)
    for i in index:
        areas[i["area"]][i["verification"]] += 1
    coverage = {
        "total_actions": len(index),
        "by_verification": dict(by_status),
        "by_route_kind": dict(by_route),
        "without_public_api": len(ui_only),
        "curated_entries": n_curated,
        "web_app_walk": ui_walk,
        "by_area": {a: dict(c) for a, c in sorted(areas.items())},
    }
    findings = catalog_lint.as_dicts(catalog_lint.lint(actions))
    coverage["lint"] = dict(Counter(f"{f['check']} ({f['severity']})" for f in findings))
    (ROOT / "catalog/lint.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "catalog/coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    print(json.dumps({k: v for k, v in coverage.items() if k != "by_area"}, indent=2))
    for change in corrections.sync(findings, "catalog_lint", catalog_lint.BUILD_CHECKS):
        print("ledger:", change)
    corrections.render()
    make_claims.main()


if __name__ == "__main__":
    main()
