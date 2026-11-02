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
    api_action = {"id": "brevo.contacts.create_list", "routes": [{"kind": "documented_api"}]}
    lines = [
        {"area": "Lists", "ui": "Create a list", "steps": ["Open the lists page", "Click 'Create a list'"], "catalog_id": api_action["id"]},
        {"area": "Lists", "ui": "Duplicate", "steps": ["Open the lists page", "Click 'Duplicate'"],
         "new": {"id": "brevo.contacts.duplicate_list", "entity": "list", "operation_class": "create", "description": "Copy a list."}},
        {"area": "Lists", "ui": "Recalculate now", "steps": ["Click 'Recalculate now'"], "kind": "view"},
    ]
    monkeypatch.setattr(build_catalog, "UI_MAP", write_map(tmp_path, lines))
    actions = {api_action["id"]: api_action}

    stats = build_catalog.apply_ui_map(actions)

    assert {r["kind"] for r in api_action["routes"]} == {"documented_api", "ui_path"}
    seen = actions["brevo.contacts.duplicate_list"]
    assert seen["verification"]["status"] == "seen"
    assert seen["side_effects"]["requires_confirmation"] is True
    schema = json.loads((ROOT / "catalog/schema/business_action.schema.json").read_text())
    jsonschema.validate(seen, schema)
    assert stats == {"business_actions": 2, "in_catalog_with_public_api": 1, "seen_only": 1, "view_only": 1}
