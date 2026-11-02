"""The MCP server applies the catalog's rules on every call.
None of these tests calls Brevo: each refusal happens before any request."""

import subprocess
import sys
from pathlib import Path

import httpx

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
        "Add zz-catalog-test-demo@example.com to the list named zz-catalog-test-demo-list. Create the contact if it does not exist.":
            "brevo.contacts.add_contact_to_list",
        "Mark the task named zz-catalog-test-demo-task as done.": "brevo.tasks.update_task",
        "Delete the contact list named zz-catalog-test-demo-list.": "brevo.contacts.delete_list",
        "Create a segment of the contacts who opened last week's campaign.": "brevo.segments.create_segment",
        "add a contact to the newsletter list": "brevo.contacts.add_contact_to_list",
        "mark a task as done": "brevo.tasks.update_task",
        "which webhooks do we have": "brevo.webhooks.get_webhooks",
        "delete the old sign-up form": "brevo.forms.delete_form",
        "which lists do we have": "brevo.contacts.get_lists",
        "which forms do we have": "brevo.forms.list_forms",
        "rename the welcome automation": "brevo.automations.rename_automation",
        "show me the transactional emails sent to bob@example.com": "brevo.transactional_emails.get_transac_emails_list",
        "list my email campaigns": "brevo.email_campaigns.get_email_campaigns",
        "delete the contact jane@example.com": "brevo.contacts.delete_contact",
        "create a contact list called VIP": "brevo.contacts.create_list",
    }
    for request, expected in cases.items():
        assert mcp_server.find_actions(request, limit=3)[0]["id"] == expected, request


def test_a_missing_api_key_is_a_refusal_not_a_crash(monkeypatch):
    # No env key and a keychain lookup that fails: the real api_key() runs.
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.setattr(mcp_server.brevo_exec.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="not found"))
    reply = mcp_server.run_action("brevo.contacts.get_lists", {})
    assert reply["ran"] is False and reply["reason"].startswith("No Brevo API key")


def test_plural_requests_do_not_push_writes_up():
    ids = [e["id"] for e in mcp_server.find_actions("which forms do we have", limit=3)]
    assert "brevo.forms.duplicate_form" not in ids[:2]


def test_irreversible_write_does_not_run_without_confirmation():
    inputs = {"email": "zz-catalog-test@example.com", "all_features_access": True, "privileges": []}
    reply = mcp_server.run_action("brevo.user.edit_user_permission", inputs)
    assert reply["ran"] is False and "confirmation" in reply["reason"]


def test_inputs_that_break_the_schema_do_not_run_even_when_confirmed():
    reply = mcp_server.run_action("brevo.user.edit_user_permission", {}, confirmed=True)
    assert reply["ran"] is False and any("required" in e for e in reply["errors"])
    reply = mcp_server.run_action("brevo.contacts.get_lists", {"limt": 5})
    assert reply["ran"] is False and "unknown inputs ['limt']" in reply["errors"][0]


def test_a_rule_seen_live_is_checked_before_the_call():
    # The API answered 400 to a transactional log query with no email, messageId or templateId.
    reply = mcp_server.run_action("brevo.transactional_emails.get_transac_emails_list", {"limit": 10})
    assert reply["ran"] is False and reply["errors"] == ["inputs: needs one of: email; messageId; templateId"]


def test_bodies_that_the_spec_writes_as_one_of_overlapping_branches_pass():
    action = mcp_server.load("brevo.contacts.add_contact_to_list")
    inputs = {"listId": 2, "body": {"emails": ["zz-catalog-test@example.com"]}}
    assert mcp_server.brevo_exec.input_errors(action, inputs) == []


def test_path_values_are_encoded_except_email_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_server.brevo_exec, "EVIDENCE", tmp_path / "runs.jsonl")
    seen = []
    transport = httpx.MockTransport(lambda request: seen.append(request.url.raw_path) or httpx.Response(404))
    with httpx.Client(transport=transport) as client:
        mcp_server.brevo_exec.call("brevo.contacts.get_contact_info", {"identifier": "a+b@example.com"}, client, "test")
        mcp_server.brevo_exec.call("brevo.contacts.get_contact_info", {"identifier": "x/../y"}, client, "test")
    assert seen[0].endswith(b"/contacts/a+b@example.com") and seen[1].endswith(b"/contacts/x%2F..%2Fy")


def test_a_network_error_is_a_refusal_not_a_crash(monkeypatch):
    def broken():
        return httpx.Client(transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("down"))))

    monkeypatch.setattr(mcp_server.brevo_exec, "client", broken)
    reply = mcp_server.run_action("brevo.contacts.get_lists", {})
    assert reply["ran"] is False and "did not complete" in reply["reason"]
