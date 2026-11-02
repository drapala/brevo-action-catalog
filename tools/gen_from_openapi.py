"""Generate draft business actions from Brevo's official OpenAPI spec.

Deterministic: no LLM. Every field comes from the spec or from a rule in this
file, so a reviewer can trace each value. Entries start as `documented`; the
verifier and the UI walk upgrade them later.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog_lint import DESTRUCTIVE_NAME  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "sources/openapi/brevo-v3.yml"
OUT = ROOT / "build/openapi_actions"
BASE_URL = "https://api.brevo.com/v3"
METHODS = ("get", "post", "put", "patch", "delete")

# Last path segments that name a verb, not a resource.
VERB_SEGMENTS = {
    "add",
    "remove",
    "sendNow",
    "sendTest",
    "sendReport",
    "status",
    "export",
    "exportRecipients",
    "import",
    "validate",
    "authenticate",
    "publish",
    "cancel",
    "complete",
    "redeem",
    "revoke",
    "activate",
    "upsert",
    "delete",
    "toggle",
    "plan",
    "associate",
    "dissociate",
    "send",
    "approval",
    "unlink",
    "link-unlink",
    "agentOnlinePing",
    "preview",
    "deleteHardbounces",
    "doubleOptinConfirmation",
    "sendMessage",
    "create-order",
    "attribute",
    "ssoToken",
    "key",
    "installUrl",
    "batch",
}

# Areas that need an app, a setup step, or a paid plan before any call works.
AREA_REQUIRES = {
    "Master account": ["Enterprise master account"],
    "Program": ["Loyalty app activated"],
    "Reward": ["Loyalty app activated"],
    "Tier": ["Loyalty app activated"],
    "Balance": ["Loyalty app activated"],
    "Wallet": ["Wallet passes configured"],
    "Payments": ["Brevo Payments activated"],
    "Ecommerce": ["eCommerce app activated"],
    "Coupons": ["eCommerce app activated"],
    "WhatsApp Campaigns": ["WhatsApp Business account connected"],
    "Transactional WhatsApp": ["WhatsApp Business account connected"],
    "Inbound Parsing": ["Inbound parsing webhook configured"],
    "Conversations": ["Conversations chat widget installed"],
    "Custom Objects": ["Custom objects enabled"],
    "Event": ["Events tracking enabled"],
}

SEND_EFFECTS = [
    # (method, path regex, effect)
    (
        "POST",
        r"^/emailCampaigns/\{campaignId\}/(sendNow|sendTest|sendReport)$",
        "sends_email",
    ),
    ("POST", r"^/smtp/email$", "sends_email"),
    ("POST", r"^/smtp/templates/\{templateId\}/sendTest$", "sends_email"),
    ("POST", r"^/contacts/doubleOptinConfirmation$", "sends_email"),
    ("POST", r"^/smsCampaigns/\{campaignId\}/(sendNow|sendTest)$", "sends_sms"),
    ("POST", r"^/smsCampaigns/\{campaignId\}/sendReport$", "sends_email"),
    ("POST", r"^/transactionalSMS/(sms|send)$", "sends_sms"),
    ("POST", r"^/whatsappCampaigns$", "sends_whatsapp"),
    ("POST", r"^/whatsapp/sendMessage$", "sends_whatsapp"),
    ("POST", r"^/(organization|corporate)/user/invitation/send$", "notifies_people"),
    (
        "PUT",
        r"^/(organization|corporate)/user/invitation/\{action\}/\{email\}$",
        "notifies_people",
    ),
    ("POST", r"^/conversations/(messages|pushedMessages)$", "notifies_people"),
    ("POST", r"^/loyalty/config/programs/\{pid\}/publish$", "publishes"),
    ("POST", r"^/senders/domains$", "changes_account"),
    ("PUT", r"^/corporate/sub[Aa]ccounts?(/\{id\})?/plan$", "changes_account"),
    (
        "POST",
        r"^/corporate/(subAccount/ssoToken|ssoToken|subAccount/key)$",
        "changes_account",
    ),
]

# Entity name for an ID path parameter, when the parameter name alone says it.
PARAM_ENTITY = {
    "listId": "list",
    "folderId": "folder",
    "senderId": "sender",
    "webhookId": "webhook",
    "domainName": "sender_domain",
    "processId": "process",
    "pipelineID": "pipeline",
    "attributeName": "contact_attribute",
    "groupId": "sub_account_group",
}

STOPWORDS = {"a", "an", "the", "s", "its", "your", "based"}



def slug(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return "_".join(w for w in words if w not in STOPWORDS)


def singular(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "ches")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


class Resolver:
    def __init__(self, spec: dict) -> None:
        self.spec = spec

    def resolve(self, node, depth: int = 0, seen: tuple = ()):
        if depth > 6:
            return {"description": "(nested schema truncated)"}
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if ref in seen:
                    return {"description": f"(recursive reference to {ref.split('/')[-1]})"}
                target = self.spec
                for part in ref.lstrip("#/").split("/"):
                    target = target[part]
                return self.resolve(target, depth + 1, seen + (ref,))
            return {k: self.resolve(v, depth + 1, seen) for k, v in node.items() if k not in ("xml",)}
        if isinstance(node, list):
            return [self.resolve(v, depth + 1, seen) for v in node]
        return node


def entity_from_path(path: str, area: str) -> str:
    segments = [s for s in path.strip("/").split("/") if s]
    resources = [s for s in segments if not s.startswith("{") and s not in VERB_SEGMENTS]
    if not resources:
        return slug(area)
    last = resources[-1]
    prev = resources[-2] if len(resources) > 1 else ""
    special = {
        ("contacts", "attributes"): "contact_attribute",
        ("crm", "attributes"): "crm_attribute",
        ("smtp", "templates"): "email_template",
        ("smtp", "template"): "email_template",
        ("whatsappCampaigns", "template"): "whatsapp_template",
        ("whatsappCampaigns", "template-list"): "whatsapp_template",
        ("transactionalSMS", "templates"): "sms_template",
        ("smtp", "email"): "transactional_email",
        ("smtp", "emails"): "transactional_email",
        ("smtp", "emailStatus"): "scheduled_email",
        ("smtp", "blockedContacts"): "blocked_contact",
        ("smtp", "blockedDomains"): "blocked_domain",
        ("senders", "domains"): "sender_domain",
        ("crm", "deals"): "deal",
        ("crm", "tasks"): "task",
        ("crm", "notes"): "note",
        ("crm", "files"): "file",
        ("crm", "tasktypes"): "task_type",
        ("orders", "status"): "order",
        ("inbound", "events"): "inbound_email_event",
    }
    if (prev, last) in special:
        return special[(prev, last)]
    if last in ("emailCampaigns",):
        return "email_campaign"
    if last == "smsCampaigns":
        return "sms_campaign"
    if last == "whatsappCampaigns":
        return "whatsapp_campaign"
    return slug(singular(last)) or slug(area)


def operation_class(method: str, path: str, summary: str) -> str:
    last = path.rstrip("/").split("/")[-1]
    lower = (summary or "").lower()
    if method == "GET":
        return "read"
    if method == "DELETE":
        return "delete"
    if method in ("PUT", "PATCH"):
        if last in VERB_SEGMENTS and last not in ("status", "plan", "toggle"):
            return "action"
        return "update"
    # POST
    if last in VERB_SEGMENTS or any(
        w in lower
        for w in (
            "send",
            "export",
            "import",
            "validate",
            "generate",
            "redeem",
            "complete",
            "cancel",
            "activate",
            "publish",
            "preview",
            "associate",
        )
    ):
        if lower.startswith(("create", "upload")) and "send" not in lower:
            return "create"
        if "update multiple" in lower:
            return "update"
        return "action"
    return "create"


def effect_for(method: str, path: str) -> str:
    for m, rx, effect in SEND_EFFECTS:
        if m == method and re.search(rx, path):
            return effect
    return "none"


def build_inputs(op: dict, path_item: dict, resolver: Resolver) -> tuple[dict, dict]:
    props: dict = {}
    required: list[str] = []
    params_loc: dict = {}
    for param in (path_item.get("parameters") or []) + (op.get("parameters") or []):
        p = resolver.resolve(param)
        name = p["name"]
        if p.get("in") == "header":
            continue
        schema = dict(p.get("schema") or {})
        if p.get("description"):
            schema["description"] = p["description"].strip()[:400]
        props[name] = schema
        params_loc[name] = p["in"]
        if p.get("required"):
            required.append(name)
    body = op.get("requestBody")
    if body:
        body = resolver.resolve(body)
        content = body.get("content", {})
        media = content.get("application/json") or next(iter(content.values()), {})
        bschema = media.get("schema") or {}
        if bschema.get("type") == "object" or "properties" in bschema:
            for name, s in (bschema.get("properties") or {}).items():
                props[name] = s
                params_loc[name] = "body"
            required += [r for r in bschema.get("required", []) if r not in required]
        elif bschema:
            props["body"] = bschema
            params_loc["body"] = "body"
            if body.get("required"):
                required.append("body")
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema, params_loc


def success_response(op: dict, resolver: Resolver) -> tuple[list[int], dict | None]:
    statuses, schema = [], None
    for code, resp in (op.get("responses") or {}).items():
        if str(code).startswith("2"):
            statuses.append(int(code))
            resp = resolver.resolve(resp)
            content = (resp.get("content") or {}).get("application/json") or {}
            if schema is None and content.get("schema"):
                schema = content["schema"]
    return statuses or [200], schema


def main() -> None:
    spec = yaml.safe_load(SPEC.read_text())
    resolver = Resolver(spec)
    drafts = []
    for path, item in spec["paths"].items():
        for method in METHODS:
            if method not in item:
                continue
            op = item[method]
            m = method.upper()
            area = (op.get("tags") or ["Other"])[0]
            area = "Companies" if area == "companies" else area
            summary = (op.get("summary") or "").strip()
            entity = entity_from_path(path, area)
            oclass = operation_class(m, path, summary)
            inputs_schema, params_loc = build_inputs(op, item, resolver)
            statuses, out_schema = success_response(op, resolver)
            name = op.get("operationId") or summary
            action_id = f"brevo.{slug(area)}.{slug(name)}"
            drafts.append(
                {
                    "m": m,
                    "path": path,
                    "area": area,
                    "entity": entity,
                    "oclass": oclass,
                    "summary": summary,
                    "op": op,
                    "id": action_id,
                    "inputs": inputs_schema,
                    "params": params_loc,
                    "statuses": statuses,
                    "out": out_schema,
                }
            )

    # Disambiguate duplicate ids.
    seen = defaultdict(int)
    for d in drafts:
        seen[d["id"]] += 1
    for d in drafts:
        if seen[d["id"]] > 1:
            d["id"] = f"{d['id']}_{d['m'].lower()}"

    # Lookup tables to link entities to the actions that list, get, create and delete them.
    by_entity = defaultdict(list)
    for d in drafts:
        by_entity[d["entity"]].append(d)

    def find_lister(entity: str):
        """A read that lists the entity and needs no other ID, or None when the API has no such route."""
        candidates = [
            d for d in by_entity.get(entity, [])
            if d["oclass"] == "read"
            and not any(loc == "path" and name in d["inputs"].get("required", []) for name, loc in d["params"].items())
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda d: len(d["path"]))["id"]

    def find_action(entity: str, oclass: str, single: bool | None = None):
        candidates = []
        for d in by_entity.get(entity, []):
            if d["oclass"] != oclass:
                continue
            ends_with_param = d["path"].rstrip("/").endswith("}")
            if single is None or single == ends_with_param:
                candidates.append(d)
        if not candidates:
            return None
        # Prefer the plainest route: fewest path parameters, then shortest path.
        best = min(candidates, key=lambda d: (d["path"].count("{"), len(d["path"])))
        return best["id"]

    ids = {d["id"].split(".")[-1]: d for d in drafts}

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    written = 0
    for d in drafts:
        refs = []
        for pname, loc in d["params"].items():
            if loc != "path":
                continue
            ent = PARAM_ENTITY.get(pname)
            if ent is None and pname in (
                "id",
                "identifier",
                "uuid",
                "campaignId",
                "templateId",
            ):
                ent = d["entity"]
            if ent is None:
                ent = slug(re.sub(r"Id$|ID$", "", pname)) or pname
            refs.append(
                {
                    "input": pname,
                    "entity": ent,
                    "find_with": find_lister(ent),
                    "create_with": find_action(ent, "create"),
                }
            )

        effect = effect_for(d["m"], d["path"])
        if d["oclass"] == "create":
            undo = find_action(d["entity"], "delete")
            reversible = undo is not None
        elif d["oclass"] in ("read",):
            undo, reversible = None, True
        elif d["oclass"] == "update":
            undo, reversible = d["id"], True
        else:
            undo, reversible = None, False
        name = d["id"].split(".")[-1]
        if name.startswith("add_") and "_to_" in name:
            undo = ids.get(name.replace("add_", "remove_", 1).replace("_to_", "_from_", 1), {}).get("id")
            reversible = undo is not None
        elif name.startswith("remove_") and "_from_" in name:
            undo = ids.get(name.replace("remove_", "add_", 1).replace("_from_", "_to_", 1), {}).get("id")
            reversible = undo is not None
        if effect != "none":
            reversible, undo = False, None
        destructive = d["oclass"] == "delete" or DESTRUCTIVE_NAME.search(name) is not None
        requires_confirmation = effect != "none" or destructive or "and all its" in d["summary"].lower()

        produces = None
        out = d["out"] or {}
        if d["oclass"] == "create" and isinstance(out, dict) and "id" in (out.get("properties") or {}):
            produces = {"entity": d["entity"], "id_field": "id"}

        get_one = find_action(d["entity"], "read", single=True)
        post = None
        if d["oclass"] in ("create", "update") and get_one:
            post = {
                "check_with": get_one,
                "assert": "the entity exists and its fields equal the inputs that were sent",
            }
        elif d["oclass"] == "delete" and get_one:
            post = {"check_with": get_one, "assert": "the read returns 404"}

        description = (d["op"].get("description") or d["summary"]).strip()
        description = re.sub(r"\s+", " ", description)[:600]
        requires = AREA_REQUIRES.get(d["area"], [])
        action = {
            "id": d["id"],
            "product": "brevo",
            "area": d["area"],
            "entity": d["entity"],
            "operation_class": d["oclass"],
            "label": d["summary"] or d["id"],
            "description": description,
            "inputs": {
                "schema": d["inputs"],
                "entity_refs": refs,
                "credential_ref": "brevo_api_key",
            },
            "outputs": {"schema": d["out"], "produces_entity": produces},
            "routes": [
                {
                    "kind": "documented_api",
                    "method": d["m"],
                    "url": BASE_URL + d["path"],
                    "auth": "header api-key",
                    "params": d["params"],
                    "success_status": d["statuses"],
                }
            ],
            "preconditions": [f"{r} (needed before any call in this area)" for r in requires],
            "postcondition": post,
            "side_effects": {
                "reversible": reversible,
                "undo_with": undo,
                "external_effect": effect,
                "idempotent": True if d["m"] in ("GET", "PUT", "DELETE") else None,
                "requires_confirmation": requires_confirmation,
            },
            "availability": {"free_plan": "unknown", "requires": requires},
            "verification": {
                "status": "documented",
                "route_kind": None,
                "checked_at": None,
                "evidence": None,
            },
            "sources": [
                {
                    "kind": "openapi",
                    "ref": f"swagger_definition_v3.yml#/paths/{d['path']}/{d['m'].lower()}"
                    + (f" ({d['op'].get('operationId')})" if d["op"].get("operationId") else ""),
                }
            ],
        }
        (OUT / f"{d['id']}.json").write_text(json.dumps(action, indent=2, ensure_ascii=False) + "\n")
        written += 1
    print(f"wrote {written} actions")
    import catalog_lint
    import corrections

    noop = catalog_lint.generator_noop(Path(__file__), OUT, ROOT / "build/generator_stamp.json")
    for change in corrections.sync(catalog_lint.as_dicts(noop), "catalog_lint", {"L006"}):
        print("ledger:", change)


if __name__ == "__main__":
    main()
