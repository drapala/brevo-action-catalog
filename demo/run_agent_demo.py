"""Give a fresh Claude agent four user requests and only the catalog's MCP tools.

Each request runs in its own headless session. The script writes every tool call,
its reply, and the agent's final answer to demo/agent-demo-<date>.md.

Usage: .venv/bin/python demo/run_agent_demo.py
Needs: the `claude` CLI logged in, and a Brevo API key (see README).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = "brevo-catalog"
TOOLS = [f"mcp__{SERVER}__{t}" for t in ("find_actions", "get_action", "run_action")]

SYSTEM = (
    "You operate the Brevo account of a user through the brevo-catalog tools. Use only these tools. "
    "Before you run an action, read its catalog entry with get_action and follow it: look up IDs with the finder "
    "it names, respect its verification status and notes, and do the read-back it gives before you report success. "
    "The user cannot answer during this session. If an action needs the user's confirmation, do not set "
    "confirmed=true; stop and write the question you would ask. Answer in English, in at most six short sentences, "
    "and say what you checked."
)

REQUESTS = [
    "Add zz-catalog-test-demo@example.com to the list named zz-catalog-test-demo-list. Create the contact if it does not exist.",
    "Mark the task named zz-catalog-test-demo-task as done.",
    "Delete the contact list named zz-catalog-test-demo-list.",
    "Create a segment of the contacts who opened last week's campaign.",
]


def run(request: str, config: Path) -> tuple[list[dict], str]:
    cmd = ["claude", "-p", request, "--system-prompt", SYSTEM, "--mcp-config", str(config), "--strict-mcp-config",
           "--allowedTools", ",".join(TOOLS), "--output-format", "stream-json", "--verbose", "--max-turns", "30"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp", timeout=900)
    except subprocess.TimeoutExpired:
        return [], "(the agent did not finish within 15 minutes)"
    steps, final = [], ""
    pending = {}
    for line in out.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "assistant":
            for block in event["message"]["content"]:
                if block.get("type") == "tool_use" and block["name"].startswith("mcp__"):
                    pending[block["id"]] = {"tool": block["name"].split("__")[-1], "input": block["input"]}
        elif event.get("type") == "user":
            for block in event["message"]["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    call = pending.pop(block["tool_use_id"], None)
                    if call is None:
                        continue
                    content = block.get("content")
                    text = content if isinstance(content, str) else " ".join(c.get("text", "") for c in content or [])
                    steps.append({**call, "result": text})
        elif event.get("type") == "result":
            final = event.get("result", "")
            if event.get("is_error"):
                final = f"(the agent session ended with an error) {final}"
    if out.returncode != 0 and not final:
        final = f"(claude exited with code {out.returncode}: {out.stderr.strip()[:300]})"
    for call in pending.values():
        steps.append({**call, "result": "(no reply recorded)"})
    return steps, final


def short(text: str, limit: int = 600) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + " ..."


def main() -> None:
    config = Path("/tmp/brevo-catalog-mcp.json")
    config.write_text(json.dumps({"mcpServers": {SERVER: {"command": str(ROOT / ".venv/bin/python"),
                                                           "args": [str(ROOT / "tools/mcp_server.py")]}}}))
    lines = [f"# Agent demo, {date.today().isoformat()}", "",
             "A fresh Claude agent got each request with only three tools: `find_actions`, `get_action` and "
             "`run_action` from `tools/mcp_server.py`. It had no other context. Its instructions:", "", f"> {SYSTEM}", ""]
    for i, request in enumerate(REQUESTS, 1):
        print(f"[{i}] {request}", file=sys.stderr)
        steps, final = run(request, config)
        lines += [f"## {i}. \"{request}\"", "", "| # | Tool | Input | Reply |", "|---|---|---|---|"]
        for n, s in enumerate(steps, 1):
            lines.append(f"| {n} | `{s['tool']}` | `{short(json.dumps(s['input']), 200)}` | {short(s['result'], 400).replace('|', '/')} |")
        lines += ["", "**Agent's answer:**", "", final.strip(), ""]
    out = ROOT / f"demo/agent-demo-{date.today().isoformat()}.md"
    out.write_text("\n".join(lines) + "\n")
    print(out)


if __name__ == "__main__":
    main()
