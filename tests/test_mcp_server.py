"""The MCP server enforces the catalog's rules, so an agent cannot skip them.
None of these tests calls Brevo: each refusal happens before any request."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import mcp_server  # noqa: E402


def test_action_that_needs_confirmation_does_not_run_without_it():
    reply = mcp_server.run_action("brevo.contacts.delete_list", {"listId": 1})
    assert reply["ran"] is False and "confirmation" in reply["reason"]


def test_seen_action_does_not_run_and_returns_the_ui_steps():
    reply = mcp_server.run_action("brevo.segments.rename_segment", {})
    assert reply["ran"] is False and "seen" in reply["reason"] and reply["ui_paths"]


def test_gated_action_with_a_public_api_does_not_run():
    reply = mcp_server.run_action("brevo.ecommerce.get_orders", {}, confirmed=True)
    assert reply["ran"] is False and "gated" in reply["reason"]


def test_ui_only_action_does_not_run_even_when_confirmed():
    reply = mcp_server.run_action("brevo.forms.delete_form", {"formId": "x"}, confirmed=True)
    assert reply["ran"] is False and "no public API" in reply["reason"]


def test_requests_from_the_reviewer_find_the_right_action_first():
    cases = {
        "add a contact to the newsletter list": "brevo.contacts.add_contact_to_list",
        "mark a task as done": "brevo.tasks.update_task",
        "which webhooks do we have": "brevo.webhooks.get_webhooks",
        "delete the old sign-up form": "brevo.forms.delete_form",
        "which lists do we have": "brevo.contacts.get_lists",
        "which forms do we have": "brevo.forms.list_forms",
    }
    for request, expected in cases.items():
        assert mcp_server.find_actions(request, limit=3)[0]["id"] == expected, request


def test_a_missing_api_key_is_a_refusal_not_a_crash(monkeypatch):
    def no_key():
        raise RuntimeError("No Brevo API key")
    monkeypatch.setattr(mcp_server.brevo_exec, "api_key", no_key)
    reply = mcp_server.run_action("brevo.contacts.get_lists", {})
    assert reply == {"ran": False, "reason": "No Brevo API key"}


def test_plural_requests_do_not_push_writes_up():
    ids = [e["id"] for e in mcp_server.find_actions("which forms do we have", limit=3)]
    assert "brevo.forms.duplicate_form" not in ids[:2]
