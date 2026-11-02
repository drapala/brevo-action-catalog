"""MCP server that lets an AI agent use the catalog to operate Brevo.

The agent finds an action, reads its entry, runs it, and checks the effect. The
server applies the catalog's rules on every call:
  - inputs that break the entry's input schema do not run;
  - an action that needs confirmation runs only with confirmed=true;
  - a gated, seen or UI-only action does not run, and the reply says why;
  - a run returns the read-back to do before reporting success, when the entry has one.
  - a write that was sent but got no answer is reported as unknown, with the check to do before a retry.
confirmed=true is the agent's statement that the user agreed. The server cannot check
it, so the MCP client's approval prompt for each tool call is where a person checks it.

Run: .venv/bin/python tools/mcp_server.py   (stdio)
The Brevo API key comes from BREVO_API_KEY or the macOS keychain, as in brevo_exec.py.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx
from fastmcp import FastMCP

import brevo_exec

ROOT = Path(__file__).resolve().parent.parent
ACTIONS = ROOT / "catalog/actions"
INDEX = ROOT / "catalog/index.json"
RUN = f"mcp-{int(time.time())}"

mcp = FastMCP("brevo-catalog")


def load(action_id: str) -> dict | None:
    path = ACTIONS / f"{action_id}.json"
    return json.loads(path.read_text()) if path.exists() else None


# Words a user says for an operation, mapped to the words in action ids and labels.
SYNONYMS = {
    "mark": "update",
    "done": "update",
    "complete": "update",
    "rename": "update",
    "edit": "update",
    "change": "update",
    "remove": "delete",
    "which": "get",
    "show": "get",
}


def ui_paths(action: dict) -> list[list[str]]:
    return [r["ui_steps"] for r in action["routes"] if r["kind"] == "ui_path"]


STOPWORDS = {"the", "and", "for", "our", "you", "your", "with", "from", "this", "that", "all", "any", "have", "has"}


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) <= 2 or w in STOPWORDS:
            continue
        w = w[:-1] if w.endswith("s") and not w.endswith("ss") else w
        out |= {w, SYNONYMS.get(w, w)}
    return out


@mcp.tool
def find_actions(request: str, limit: int = 8) -> list[dict]:
    """Find catalog actions for a user's request, best match first.

    Each result has the id, label, area, verification status, free-plan availability
    and the confirmation flag. Read the full entry with get_action before you run it.
    """
    wanted = words(request)
    tokens = re.findall(r"[a-z]+", request.lower())
    lead = SYNONYMS.get(tokens[0], tokens[0]) if tokens else ""
    plural = {w[:-1] for w in re.findall(r"[a-z]+", request.lower()) if w.endswith("s") and not w.endswith("ss")}
    scored = []
    for entry in json.loads(INDEX.read_text()):
        action = load(entry["id"]) or {}
        name = " ".join([entry["id"], entry["label"], entry["entity"]])
        about = " ".join([entry["area"], action.get("description", "")] + action.get("intent_examples", []))
        score = 2 * len(wanted & words(name)) + len(wanted & words(about))
        if score:
            trust = {"verified": 3, "observed": 2, "failed": 2, "documented": 1}.get(entry["verification"], 0)
            required = len(action.get("inputs", {}).get("schema", {}).get("required", []))
            if entry["id"].split(".")[-1].split("_")[0] == lead:
                score += 2  # the request opens with this action's verb ("Add ..." -> add_contact_to_list)
            if entry["entity"].split("_")[-1] in wanted:
                score += 2  # the request names this action's own entity ("the contact list" -> list)
            if entry["operation_class"] == "read" and entry["entity"].split("_")[-1] in plural and not required:
                score += 3  # "which webhooks": the list action, not the get-one action
            scored.append((score, trust, required, entry))
    # Ties go to the more trusted action, then to the one that needs fewer inputs (a list before a get-by-id).
    scored.sort(key=lambda s: (-s[0], -s[1], s[2]))
    return [entry for *_, entry in scored[:limit]]


@mcp.tool
def get_action(action_id: str) -> dict:
    """Return the full catalog entry: inputs, where each ID comes from, routes, read-back, side effects, status."""
    action = load(action_id)
    if action is None:
        return {"error": f"unknown action {action_id}. Use find_actions."}
    return action


@mcp.tool
def run_action(action_id: str, inputs: dict, confirmed: bool = False) -> dict:
    """Run a catalog action through the public Brevo API.

    Set confirmed=true only after the user agreed to this exact call. The reply holds
    the HTTP status, the response, and, when the entry has one, the read-back to run before you report success.
    """
    action = load(action_id)
    if action is None:
        return {"ran": False, "reason": f"unknown action {action_id}. Use find_actions."}
    status = action["verification"]["status"]
    if status in ("gated", "seen"):
        return {
            "ran": False,
            "reason": f"status is {status}: {action['verification'].get('notes')}",
            "ui_paths": ui_paths(action),
        }
    if not any(r["kind"] == "documented_api" for r in action["routes"]):
        return {
            "ran": False,
            "reason": "this action has no public API. A browser agent must follow the UI steps.",
            "ui_paths": ui_paths(action),
        }
    errors = brevo_exec.input_errors(action, inputs)
    if errors:
        return {"ran": False, "reason": "the inputs do not match the catalog entry", "errors": errors}
    if action["side_effects"]["requires_confirmation"] and not confirmed:
        return {
            "ran": False,
            "reason": "this action needs the user's confirmation. Ask the user, then call again with confirmed=true.",
            "side_effects": action["side_effects"],
        }
    try:
        with brevo_exec.client() as c:
            code, payload = brevo_exec.call(action_id, inputs, c, RUN, action=action)
    except (RuntimeError, ValueError) as error:
        return {"ran": False, "reason": str(error)}
    except (httpx.ConnectError, httpx.ConnectTimeout) as error:
        return {"ran": False, "reason": f"the request did not reach Brevo: {error!r}"}
    except httpx.TransportError as error:
        # The request was sent, so a write may have landed. A blind retry can create a duplicate.
        if action["operation_class"] == "read":
            return {"ran": False, "reason": f"no answer from Brevo: {error!r}. A read is safe to retry."}
        check = action.get("postcondition") or {}
        return {
            "ran": "unknown",
            "reason": f"the request was sent but no answer came back: {error!r}. The action may have run.",
            "next_step": f"Before any retry, run {check['check_with']} and check: {check['assert']}"
            if check
            else "Before any retry, look the item up and check whether the action already took effect.",
        }
    reply = {"ran": True, "http_status": code, "response": payload, "catalog_status": status}
    if status == "failed":
        reply["warning"] = action["verification"].get("notes")
    if action.get("postcondition"):
        reply["next_step"] = (
            f"Before you report success, run {action['postcondition']['check_with']} and confirm: "
            f"{action['postcondition']['assert']}"
        )
    return reply


if __name__ == "__main__":
    mcp.run()
