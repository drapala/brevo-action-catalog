"""Replays the update_task case: the write call returned 204, the read-back showed
no change, and the catalog marked the write as verified. The read-back failure
must land on the write action, not on the read action that ran it."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_catalog  # noqa: E402


def entry(action_id):
    op = "read" if action_id.split(".")[-1].startswith("get_") else "update"
    return {"id": action_id, "operation_class": op, "routes": [{"kind": "documented_api", "success_status": [200]}],
            "verification": {"status": "documented"}, "availability": {"free_plan": "unknown"}}


def test_failed_read_back_marks_the_write_action_failed(tmp_path, monkeypatch):
    runs = [
        {"run": "crm-1", "step": "s", "action": "brevo.tasks.update_task", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:11:08+00:00"},
        {"run": "crm-1", "step": "s", "action": "brevo.tasks.get_task", "verdict": "fail", "at": "2026-11-02T16:11:09+00:00",
         "why": "done = False, expected True", "postcondition_of": "brevo.tasks.update_task",
         "note": "update_task answers 204 to done=true but the task stays not done"},
        {"run": "crm-1", "step": "s", "action": "brevo.tasks.get_task", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:11:10+00:00"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)

    actions = {a: entry(a) for a in ("brevo.tasks.update_task", "brevo.tasks.get_task")}
    build_catalog.apply_evidence(actions)

    assert actions["brevo.tasks.update_task"]["verification"]["status"] == "failed"
    assert "stays not done" in actions["brevo.tasks.update_task"]["verification"]["notes"]
    assert actions["brevo.tasks.get_task"]["verification"]["status"] == "verified"


def test_passing_read_back_keeps_the_write_action_verified(tmp_path, monkeypatch):
    runs = [
        {"run": "c-1", "step": "s", "action": "brevo.contacts.update_list", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:12:00+00:00"},
        {"run": "c-1", "step": "s", "action": "brevo.contacts.get_list", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:12:01+00:00",
         "postcondition_of": "brevo.contacts.update_list"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)

    actions = {a: entry(a) for a in ("brevo.contacts.update_list", "brevo.contacts.get_list")}
    build_catalog.apply_evidence(actions)

    assert actions["brevo.contacts.update_list"]["verification"]["status"] == "verified"


def test_write_without_a_read_back_is_not_verified(tmp_path, monkeypatch):
    # The reviewer found 11 writes marked verified from their own 2xx, with no read-back.
    runs = [{"run": "c-2", "step": "s", "action": "brevo.contacts.create_folder", "verdict": "pass", "why": "ok", "at": "2026-11-02T18:00:00+00:00"}]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text(json.dumps(runs[0]) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    actions = {"brevo.contacts.create_folder": entry("brevo.contacts.create_folder")}
    build_catalog.apply_evidence(actions)
    assert actions["brevo.contacts.create_folder"]["verification"]["status"] == "documented"


def test_failed_read_back_does_not_mark_the_read_action_failed(tmp_path, monkeypatch):
    runs = [
        {"run": "c-3", "step": "s", "action": "brevo.tasks.update_task", "verdict": "pass", "why": "ok", "at": "2026-11-02T18:10:00+00:00"},
        {"run": "c-3", "step": "s", "action": "brevo.tasks.get_task", "verdict": "fail", "why": "done = False", "at": "2026-11-02T18:10:01+00:00",
         "postcondition_of": "brevo.tasks.update_task"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    actions = {a: entry(a) for a in ("brevo.tasks.update_task", "brevo.tasks.get_task")}
    build_catalog.apply_evidence(actions)
    assert actions["brevo.tasks.update_task"]["verification"]["status"] == "failed"
    assert actions["brevo.tasks.get_task"]["verification"]["status"] != "failed"


def test_the_newest_own_result_wins(tmp_path, monkeypatch):
    runs = [
        {"run": "r1", "step": "s", "action": "brevo.contacts.get_lists", "verdict": "pass", "why": "ok", "at": "2026-11-02T18:00:00+00:00"},
        {"run": "r2", "step": "s", "action": "brevo.contacts.get_lists", "verdict": "fail", "why": "status 500", "at": "2026-11-02T18:05:00+00:00"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    actions = {"brevo.contacts.get_lists": entry("brevo.contacts.get_lists")}
    build_catalog.apply_evidence(actions)
    assert actions["brevo.contacts.get_lists"]["verification"]["status"] == "failed"


def test_a_passing_scenario_read_back_becomes_the_entry_postcondition_in_plain_words(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    scenarios.mkdir()
    (scenarios / "s.yaml").write_text(
        "name: demo\nsteps:\n"
        "  - {name: add, action: brevo.contacts.add_contact_to_list}\n"
        "  - {name: listed, action: brevo.contacts.get_contacts_from_list, postcondition_of: brevo.contacts.add_contact_to_list,\n"
        "     assert: {status: 200, list_contains: {path: contacts, field: email, value: x}}}\n")
    runs = [
        {"run": "demo-1", "step": "add", "action": "brevo.contacts.add_contact_to_list", "verdict": "pass", "at": "2026-11-02T18:20:00+00:00"},
        {"run": "demo-1", "step": "listed", "action": "brevo.contacts.get_contacts_from_list", "verdict": "pass",
         "postcondition_of": "brevo.contacts.add_contact_to_list", "at": "2026-11-02T18:20:01+00:00"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    monkeypatch.setattr(build_catalog, "SCENARIOS", scenarios)
    write = entry("brevo.contacts.add_contact_to_list")
    build_catalog.apply_evidence({write["id"]: write})
    assert write["postcondition"]["check_with"] == "brevo.contacts.get_contacts_from_list"
    assert "`contacts` holds an item whose `email`" in write["postcondition"]["assert"]
    assert write["verification"]["status"] == "verified"


def test_live_success_code_replaces_the_spec_code_with_a_note(tmp_path, monkeypatch):
    runs = [
        {"run": "c-4", "action": "brevo.companies.update_company", "status": 204, "expected": [200], "at": "2026-11-02T18:30:00+00:00"},
        {"run": "c-4", "step": "s", "action": "brevo.companies.update_company", "verdict": "pass", "at": "2026-11-02T18:30:01+00:00"},
        {"run": "c-4", "step": "r", "action": "brevo.companies.get_company", "verdict": "pass",
         "postcondition_of": "brevo.companies.update_company", "at": "2026-11-02T18:30:02+00:00"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    write = entry("brevo.companies.update_company")
    build_catalog.apply_evidence({write["id"]: write})
    assert write["routes"][0]["success_status"] == [204]
    assert "live API returns [204]" in write["verification"]["notes"]


def test_a_newer_own_failure_wins_over_an_older_read_probe(tmp_path, monkeypatch):
    runs = [
        {"run": "probe-reads-1", "action": "brevo.contacts.get_lists", "status": 200, "expected": [200], "at": "2026-11-02T18:00:00+00:00"},
        {"run": "r2", "step": "s", "action": "brevo.contacts.get_lists", "verdict": "fail", "why": "status 500", "at": "2026-11-02T18:05:00+00:00"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    actions = {"brevo.contacts.get_lists": entry("brevo.contacts.get_lists")}
    build_catalog.apply_evidence(actions)
    assert actions["brevo.contacts.get_lists"]["verification"]["status"] == "failed"


def test_read_back_text_covers_every_kind_of_check():
    text = build_catalog.describe_check({"status": 200, "equals": {"name": "${prefix}-x", "status": "draft"},
                                         "list_excludes": {"path": "attributes", "field": "name", "value": "X"}})
    assert "`name` equals the value that was sent" in text
    assert '`status` equals "draft"' in text
    assert "`attributes` no longer holds an item whose `name`" in text
    assert build_catalog.describe_check({"status": 404}) == "the read returns HTTP 404"


def test_a_plan_refusal_marks_gated_and_any_other_answer_keeps_documented(tmp_path, monkeypatch):
    # A call that cannot succeed only tells whether the free plan refuses the route. It never verifies.
    runs = [
        {"run": "probe-gates-1", "action": "brevo.tier.get_tier", "status": 403, "at": "2026-11-02T19:50:00+00:00",
         "response": {"message": "Current account is not activated for this feature"}},
        {"run": "probe-gates-1", "action": "brevo.files.get_file", "status": 404, "at": "2026-11-02T19:50:01+00:00",
         "response": {"code": "document_not_found"}},
        # A 403 that rejects the fake input is not a plan refusal.
        {"run": "probe-gates-1", "action": "brevo.user.get_invite", "status": 403, "at": "2026-11-02T19:50:02+00:00",
         "response": {"code": "bad_request", "message": "Invalid request"}},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)
    actions = {a: entry(a) for a in ("brevo.tier.get_tier", "brevo.files.get_file", "brevo.user.get_invite")}
    build_catalog.apply_evidence(actions)

    tier, file = actions["brevo.tier.get_tier"], actions["brevo.files.get_file"]
    assert tier["verification"]["status"] == "gated" and tier["availability"]["free_plan"] == "gated"
    assert file["verification"]["status"] == "documented" and file["availability"]["free_plan"] == "unknown"
    assert "HTTP 404" in file["verification"]["notes"]
    assert actions["brevo.user.get_invite"]["verification"]["status"] == "documented"
