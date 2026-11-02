"""Replays the update_task case: the write call returned 204, the read-back showed
no change, and the catalog marked the write as verified. The read-back failure
must land on the write action, not on the read action that ran it."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_catalog  # noqa: E402


def entry(action_id):
    return {"id": action_id, "verification": {"status": "documented"}, "availability": {"free_plan": "unknown"}}


def test_failed_read_back_marks_the_write_action_failed(tmp_path, monkeypatch):
    runs = [
        {"run": "crm-1", "action": "brevo.tasks.update_task", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:11:08+00:00"},
        {"run": "crm-1", "action": "brevo.tasks.get_task", "verdict": "fail", "at": "2026-11-02T16:11:09+00:00",
         "why": "done = False, expected True", "postcondition_of": "brevo.tasks.update_task",
         "note": "update_task answers 204 to done=true but the task stays not done"},
        {"run": "crm-1", "action": "brevo.tasks.get_task", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:11:10+00:00"},
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
        {"run": "c-1", "action": "brevo.contacts.update_list", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:12:00+00:00"},
        {"run": "c-1", "action": "brevo.contacts.get_list", "verdict": "pass", "why": "ok", "at": "2026-11-02T16:12:01+00:00",
         "postcondition_of": "brevo.contacts.update_list"},
    ]
    evidence = tmp_path / "runs.jsonl"
    evidence.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    monkeypatch.setattr(build_catalog, "EVIDENCE", evidence)

    actions = {a: entry(a) for a in ("brevo.contacts.update_list", "brevo.contacts.get_list")}
    build_catalog.apply_evidence(actions)

    assert actions["brevo.contacts.update_list"]["verification"]["status"] == "verified"
