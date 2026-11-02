"""Mechanical checks over the catalog. Each check targets a class of error that
already happened once, so the system catches that class from then on.

A finding with severity "error" opens an entry in the corrections ledger; the
same check closes it when it passes again. Severity "gap" goes to the coverage
report only, because it marks missing work, not a wrong entry.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID_FILLERS = {"a", "an", "the"}
WEAK_ENTITY_NAMES = {"detail", "metric", "request", "group", "limit", "object", "message", "data", "info", "report"}


@dataclass(frozen=True)
class Finding:
    check: str
    target: str
    severity: str
    message: str


def camel_words(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text)]


def operation_id(action: dict) -> str | None:
    for source in action.get("sources", []):
        m = re.search(r"\((\w+)\)$", source.get("ref", ""))
        if source.get("kind") == "openapi" and m:
            return m.group(1)
    return None


def check_id_keeps_words(action: dict) -> list[Finding]:
    """L001: every word of the spec's operationId survives in the action ID."""
    op = operation_id(action)
    if not op:
        return []
    id_words = set(action["id"].split(".")[-1].split("_"))
    missing = [w for w in camel_words(op) if w not in ID_FILLERS and w not in id_words]
    if missing:
        return [Finding("L001", action["id"], "error", f"ID drops {missing} from operationId {op}")]
    return []


def check_finder_is_callable(action: dict, actions: dict[str, dict]) -> list[Finding]:
    """L002: the action named to look up a referenced ID needs no other unknown ID."""
    out = []
    for ref in action["inputs"].get("entity_refs", []):
        finder_id = ref.get("find_with")
        if not finder_id or finder_id not in actions:
            continue
        finder = actions[finder_id]
        path_params = [p for p, loc in finder["routes"][0].get("params", {}).items() if loc == "path"]
        required = set(finder["inputs"]["schema"].get("required", []))
        blocking = [p for p in path_params if p in required]
        if blocking:
            out.append(
                Finding(
                    "L002", f"{action['id']}#{ref['input']}", "error", f"finder {finder_id} itself needs {blocking}"
                )
            )
    return out


def check_effect_needs_confirmation(action: dict) -> list[Finding]:
    """L003: anything that reaches people or the account asks first."""
    se = action["side_effects"]
    if se["external_effect"] != "none" and not se["requires_confirmation"]:
        return [Finding("L003", action["id"], "error", f"{se['external_effect']} without requires_confirmation")]
    return []


DESTRUCTIVE_NAME = re.compile(r"(^|_)(delete|remove|cancel|revoke|clear|purge)(_|$)")


def check_destructive_needs_confirmation(action: dict) -> list[Finding]:
    """L007: an action that deletes or cancels something asks first, whatever its operation class."""
    name = action["id"].split(".")[-1]
    if action["operation_class"] == "read" or action["side_effects"]["requires_confirmation"]:
        return []
    if action["operation_class"] == "delete" or DESTRUCTIVE_NAME.search(name):
        return [Finding("L007", action["id"], "error", "deletes or cancels without requires_confirmation")]
    return []


def check_verified_has_evidence(action: dict) -> list[Finding]:
    """L004: no 'verified' status without an evidence pointer and a date."""
    v = action["verification"]
    if v["status"] == "verified" and not (v.get("evidence") and v.get("checked_at")):
        return [Finding("L004", action["id"], "error", "verified without evidence or date")]
    return []


def check_undo_points_to_real_action(action: dict, actions: dict[str, dict]) -> list[Finding]:
    """L005: an undo or postcondition reference names an action that exists."""
    out = []
    undo = action["side_effects"].get("undo_with")
    if undo and undo not in actions:
        out.append(Finding("L005", action["id"], "error", f"undo_with {undo} does not exist"))
    post = action.get("postcondition") or {}
    if post.get("check_with") and post["check_with"] not in actions:
        out.append(
            Finding("L005", action["id"], "error", f"postcondition check_with {post['check_with']} does not exist")
        )
    return out


def check_write_has_postcondition(action: dict) -> list[Finding]:
    """G001 (gap): a write without a way to prove it took effect."""
    if action["operation_class"] in ("create", "update", "delete") and not action.get("postcondition"):
        return [Finding("G001", action["id"], "gap", "write with no postcondition")]
    return []


def check_entity_name(action: dict) -> list[Finding]:
    """G002 (gap): entity named after a URL word, not a business object."""
    if action["entity"] in WEAK_ENTITY_NAMES:
        return [Finding("G002", action["id"], "gap", f"weak entity name '{action['entity']}'")]
    return []


def lint(actions: dict[str, dict]) -> list[Finding]:
    findings: list[Finding] = []
    for action in actions.values():
        findings += check_id_keeps_words(action)
        findings += check_finder_is_callable(action, actions)
        findings += check_effect_needs_confirmation(action)
        findings += check_destructive_needs_confirmation(action)
        findings += check_verified_has_evidence(action)
        findings += check_undo_points_to_real_action(action, actions)
        findings += check_write_has_postcondition(action)
        findings += check_entity_name(action)
    return findings


def generator_noop(gen_source: Path, output_dir: Path, stamp: Path) -> list[Finding]:
    """L006: the generator changed but its output did not, so an edit had no effect."""
    src = hashlib.sha256(gen_source.read_bytes()).hexdigest()
    out = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(output_dir.glob("*.json")))).hexdigest()
    previous = json.loads(stamp.read_text()) if stamp.exists() else None
    stamp.write_text(json.dumps({"source": src, "output": out}))
    if previous and previous["source"] != src and previous["output"] == out:
        return [Finding("L006", gen_source.name, "error", "generator source changed but its output is identical")]
    return []


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
