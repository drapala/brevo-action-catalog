"""The MCP server applies the catalog's rules on every call.
None of these tests calls Brevo: each refusal happens before any request."""

import subprocess
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import mcp_server  # noqa: E402


def refuse_request(request):
    raise AssertionError(f"a test tried to call Brevo: {request.method} {request.url}")


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    """A regression must fail the test, not reach the live account or the evidence log."""
    real_api_key = mcp_server.brevo_exec.api_key

    def offline_client():
        real_api_key()  # a missing key still raises, as in the real client()
        return httpx.Client(transport=httpx.MockTransport(refuse_request))

    monkeypatch.setattr(mcp_server.brevo_exec, "client", offline_client)
    monkeypatch.setattr(mcp_server.brevo_exec, "EVIDENCE", tmp_path / "runs.jsonl")


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


def test_one_of_bodies_accept_one_named_field_and_refuse_the_rest():
    # The spec branches each name one field and require none, so before the fix every object passed.
    add = mcp_server.load("brevo.contacts.add_contact_to_list")
    remove = mcp_server.load("brevo.contacts.remove_contact_from_list")
    errors = mcp_server.brevo_exec.input_errors
    assert errors(add, {"listId": 2, "body": {"emails": ["zz-catalog-test@example.com"]}}) == []
    assert errors(add, {"listId": 2, "body": {"ids": [7]}}) == []
    assert errors(remove, {"listId": 2, "body": {"all": True}}) == []
    for body in ({}, {"emails": "x"}, {"emial": ["zz@example.com"]}, {"emails": []}, {"ids": ["abc"]}):
        assert errors(add, {"listId": 2, "body": body}), body
    assert errors(add, {"listId": 2, "body": {}}) == ["body: needs exactly one of: emails; ids; extIds"]
    assert errors(add, {"listId": 2, "body": {"emails": "x"}}) == ["body.emails: 'x' is not of type 'array'"]
    assert errors(add, {"listId": 2, "body": {"ids": ["abc"]}}) == ["body.ids.0: 'abc' is not of type 'integer'"]


def test_a_response_that_cannot_be_decoded_is_unknown_for_a_write(monkeypatch):
    monkeypatch.setattr(mcp_server.brevo_exec, "client", failing_client(httpx.DecodingError("bad gzip")))
    reply = mcp_server.run_action("brevo.contacts.create_list", {"name": "zz-catalog-test-x", "folderId": 1})
    assert reply["ran"] == "unknown"


def test_path_values_are_encoded_except_the_at_sign():
    seen = []
    transport = httpx.MockTransport(lambda request: seen.append(request.url.raw_path) or httpx.Response(404))
    with httpx.Client(transport=transport) as client:
        mcp_server.brevo_exec.call("brevo.contacts.get_contact_info", {"identifier": "a+b@example.com"}, client, "test")
        mcp_server.brevo_exec.call("brevo.contacts.get_contact_info", {"identifier": "x/../y"}, client, "test")
    assert seen[0].endswith(b"/contacts/a%2Bb@example.com") and seen[1].endswith(b"/contacts/x%2F..%2Fy")


def failing_client(error):
    def handler(request):
        raise error

    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


def test_a_request_that_never_left_is_a_refusal(monkeypatch):
    monkeypatch.setattr(mcp_server.brevo_exec, "client", failing_client(httpx.ConnectError("down")))
    reply = mcp_server.run_action("brevo.contacts.get_lists", {})
    assert reply["ran"] is False and "did not reach Brevo" in reply["reason"]


def test_a_write_with_no_answer_is_unknown_and_names_the_check_before_a_retry(monkeypatch):
    monkeypatch.setattr(mcp_server.brevo_exec, "client", failing_client(httpx.ReadTimeout("slow")))
    reply = mcp_server.run_action("brevo.contacts.create_list", {"name": "zz-catalog-test-x", "folderId": 1})
    # get_list needs the ID that the lost response held, so the reply names the finder instead.
    assert reply["ran"] == "unknown" and reply["next_step"].startswith("Before any retry, run brevo.contacts.get_lists ")
    reply = mcp_server.run_action("brevo.contacts.update_list", {"listId": 5, "name": "zz-catalog-test-y"})
    assert reply["ran"] == "unknown" and reply["next_step"].startswith("Before any retry, run brevo.contacts.get_list ")
    reply = mcp_server.run_action("brevo.contacts.get_lists", {})
    assert reply["ran"] is False and "safe to retry" in reply["reason"]
