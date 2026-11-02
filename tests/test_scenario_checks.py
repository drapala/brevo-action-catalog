"""The read-back after a removal must fail while the item is still there, or a
removal that did nothing would pass as verified."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import brevo_exec  # noqa: E402

CHECK = {"status": 200, "list_excludes": {"path": "contacts", "field": "email", "value": "a@example.com"}}


def test_list_excludes_fails_while_the_item_is_still_listed():
    ok, why = brevo_exec.check(CHECK, 200, {"contacts": [{"email": "a@example.com"}]}, {})
    assert not ok and "still has" in why


def test_list_excludes_passes_once_the_item_is_gone():
    assert brevo_exec.check(CHECK, 200, {"contacts": [{"email": "b@example.com"}]}, {}) == (True, "ok")
