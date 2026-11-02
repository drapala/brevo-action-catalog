"""The web app walk joins every UI action to the catalog. A UI action that matches a
catalog action gives it a UI route. A UI action with no match becomes a `seen`
action that still passes the schema, so an agent can read it like any other."""

import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_catalog  # noqa: E402


def write_map(tmp_path, lines):
    path = tmp_path / "ui_map.yaml"
    path.write_text(yaml.safe_dump({"walked_at": "2026-11-02T17:05:00+00:00", "evidence": "e.json", "actions": lines}))
    return path


def test_matched_line_adds_a_ui_route_and_new_line_becomes_a_valid_seen_action(tmp_path, monkeypatch):
    api_action = {"id": "brevo.contacts.create_list", "routes": [{"kind": "documented_api"}],
                  "verification": {"status": "verified"}, "availability": {"free_plan": "available"}}
    lines = [
        {"area": "Lists", "ui": "Create a list", "steps": ["Open the lists page", "Click 'Create a list'"], "catalog_id": api_action["id"]},
        {"area": "Lists", "ui": "Duplicate", "steps": ["Open the lists page", "Click 'Duplicate'"],
         "new": {"id": "brevo.contacts.duplicate_list", "entity": "list", "operation_class": "create", "description": "Copy a list."}},
        {"area": "Lists", "ui": "Recalculate now", "steps": ["Click 'Recalculate now'"], "kind": "view"},
        # A second button for the same action counts as a web app action, not as a second catalog action.
        {"area": "Folders", "ui": "Add a list", "steps": ["Open a folder", "Click 'Add a list'"], "catalog_id": api_action["id"]},
    ]
    monkeypatch.setattr(build_catalog, "UI_MAP", write_map(tmp_path, lines))
    actions = {api_action["id"]: api_action}

    walk = build_catalog.apply_ui_map(actions)
    stats = build_catalog.walk_stats(actions, walk)

    assert {r["kind"] for r in api_action["routes"]} == {"documented_api", "ui_path"}
    seen = actions["brevo.contacts.duplicate_list"]
    assert seen["verification"]["status"] == "seen"
    assert seen["side_effects"]["requires_confirmation"] is True
    schema = json.loads((ROOT / "catalog/schema/business_action.schema.json").read_text())
    jsonschema.validate(seen, schema)
    assert stats == {"view_only": 1, "business_actions": 3, "catalog_actions": 2, "in_catalog_before_walk": 2,
                     "added_by_walk": 1, "runs_through_public_api": 2, "ui_steps_only": 1}


def test_every_ui_path_is_kept_and_a_new_action_cannot_replace_an_existing_one(tmp_path, monkeypatch):
    target = {"id": "brevo.email_campaigns.update_email_campaign", "routes": [{"kind": "documented_api"}],
              "verification": {"status": "verified"}, "availability": {"free_plan": "available"}}
    lines = [
        {"area": "Email Campaigns", "ui": "Edit", "steps": ["Click 'Edit'"], "catalog_id": target["id"]},
        {"area": "Email Campaigns", "ui": "Schedule", "steps": ["Click 'Schedule'"], "catalog_id": target["id"]},
    ]
    monkeypatch.setattr(build_catalog, "UI_MAP", write_map(tmp_path, lines))
    build_catalog.apply_ui_map({target["id"]: target})
    assert [r["ui_steps"] for r in target["routes"] if r["kind"] == "ui_path"] == [["Click 'Edit'"], ["Click 'Schedule'"]]

    clash = [{"area": "Lists", "ui": "Duplicate", "steps": ["x"],
              "new": {"id": target["id"], "entity": "list", "operation_class": "create", "description": "d"}}]
    monkeypatch.setattr(build_catalog, "UI_MAP", write_map(tmp_path, clash))
    try:
        build_catalog.apply_ui_map({target["id"]: target})
    except ValueError:
        return
    raise AssertionError("a new walk action replaced an existing catalog action")


def test_a_gated_walk_line_marks_a_documented_action_gated(tmp_path, monkeypatch):
    target = {"id": "brevo.program.create_new_lp", "routes": [{"kind": "documented_api"}],
              "verification": {"status": "documented"}, "availability": {"free_plan": "unknown"}}
    lines = [{"area": "Loyalty", "ui": "Create a loyalty program", "steps": ["Open the loyalty page"],
              "catalog_id": target["id"], "status": "gated"}]
    monkeypatch.setattr(build_catalog, "UI_MAP", write_map(tmp_path, lines))
    walk = build_catalog.apply_ui_map({target["id"]: target})
    assert target["verification"]["status"] == "gated" and target["availability"]["free_plan"] == "gated"
    assert build_catalog.walk_stats({target["id"]: target}, walk)["blocked_on_free_plan"] == 1
