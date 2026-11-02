"""Each test replays an error that happened while building the catalog and
asserts that the matching check now catches it without a human."""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import catalog_lint as lint  # noqa: E402


def action(**over):
    base = {
        "id": "brevo.contacts.add_contact_to_list",
        "entity": "contact",
        "operation_class": "action",
        "inputs": {"schema": {"type": "object", "properties": {}}, "entity_refs": []},
        "routes": [{"kind": "documented_api", "method": "POST", "url": "u", "params": {}}],
        "postcondition": None,
        "side_effects": {
            "reversible": False,
            "undo_with": None,
            "external_effect": "none",
            "requires_confirmation": False,
        },
        "verification": {"status": "documented", "evidence": None, "checked_at": None},
        "sources": [{"kind": "openapi", "ref": "swagger#/paths/x/post (addContactToList)"}],
    }
    merged = copy.deepcopy(base)
    merged.update(over)
    return merged


def test_c001_dropped_word_in_id_is_caught():
    bad = action(id="brevo.contacts.add_contact_list")
    assert [f.check for f in lint.check_id_keeps_words(bad)] == ["L001"]
    assert lint.check_id_keeps_words(action()) == []


def test_c002_finder_that_needs_another_id_is_caught():
    finder = action(
        id="brevo.contacts.get_folder_lists",
        routes=[{"kind": "documented_api", "method": "GET", "url": "u", "params": {"folderId": "path"}}],
        inputs={"schema": {"type": "object", "required": ["folderId"]}, "entity_refs": []},
    )
    user = action(
        inputs={"schema": {}, "entity_refs": [{"input": "listId", "entity": "list", "find_with": finder["id"]}]}
    )
    actions = {a["id"]: a for a in (finder, user)}
    assert [f.check for f in lint.check_finder_is_callable(user, actions)] == ["L002"]

    plain = action(id="brevo.contacts.get_lists", inputs={"schema": {"type": "object"}, "entity_refs": []})
    user_ok = action(
        inputs={"schema": {}, "entity_refs": [{"input": "listId", "entity": "list", "find_with": plain["id"]}]}
    )
    assert lint.check_finder_is_callable(user_ok, {plain["id"]: plain, user_ok["id"]: user_ok}) == []


def test_c003_generator_edit_with_no_effect_is_caught(tmp_path):
    src, out, stamp = tmp_path / "gen.py", tmp_path / "out", tmp_path / "stamp.json"
    out.mkdir()
    (out / "a.json").write_text(json.dumps({"id": "x"}))
    src.write_text("version 1")
    assert lint.generator_noop(src, out, stamp) == []
    src.write_text("version 2, same output")
    assert [f.check for f in lint.generator_noop(src, out, stamp)] == ["L006"]


def test_send_without_confirmation_is_caught():
    bad = action(
        side_effects={
            "reversible": False,
            "undo_with": None,
            "external_effect": "sends_email",
            "requires_confirmation": False,
        }
    )
    assert [f.check for f in lint.check_effect_needs_confirmation(bad)] == ["L003"]


def test_verified_without_evidence_is_caught():
    bad = action(verification={"status": "verified", "evidence": None, "checked_at": None})
    assert [f.check for f in lint.check_verified_has_evidence(bad)] == ["L004"]


def test_dangling_undo_is_caught():
    bad = action(
        side_effects={
            "reversible": True,
            "undo_with": "brevo.nope",
            "external_effect": "none",
            "requires_confirmation": False,
        }
    )
    assert [f.check for f in lint.check_undo_points_to_real_action(bad, {bad["id"]: bad})] == ["L005"]


def test_l007_delete_named_action_without_confirmation_is_caught():
    # Class "action", so the delete-class rule missed it.
    entry = action(id="brevo.transactional_emails.delete_hardbounces")
    assert [f.check for f in lint.check_destructive_needs_confirmation(entry)] == ["L007"]
    entry["side_effects"]["requires_confirmation"] = True
    assert lint.check_destructive_needs_confirmation(entry) == []
