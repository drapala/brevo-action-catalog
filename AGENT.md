# AGENT.md: read this first if you are an AI agent

This repository is a catalog of Brevo business actions, built for AI agents. It is a take-home submission for Monarch (brief: "Map a real system into an agent-ready catalog", target Brevo, scored on coverage, reliability and use of AI). This file tells you how to review it, how to use it, and how to check every claim about it.

## 0. If you are reviewing this submission

| Brief criterion | Where to look | Claims to check |
|---|---|---|
| Coverage: "How much of what a user can do in Brevo did you find?" | `sources/ui/ui_map.yaml`, `evidence/ui-walk-*.json`, `catalog/coverage.json` (`web_app_walk`) | `web_app_actions`, `web_app_catalog_actions`, `web_app_actions_with_public_api`, `actions_total` |
| Reliability: "act on it without a human double checking" | `verification` in each entry, `evidence/runs.jsonl`, `scenarios/*.yaml`, section 2 below | `status_*`, `verified_writes`, `verified_writes_without_read_back`, `live_api_calls` |
| Use of AI: "the system you designed, not only the output" | `docs/AI_LOG.md`, `docs/corrections.jsonl`, `tools/catalog_lint.py`, `tests/` | `corrections`, `corrections_with_check`, `lint_errors` |
| Agent-ready format | `catalog/schema/business_action.schema.json`, `catalog/index.json`, `tools/mcp_server.py`, sections 3 and 4 below | `requires_confirmation` |

The current values, generated from `catalog/claims.json` by the build (do not edit by hand):

<!-- claims:start -->
| Claim | Value | Meaning |
|---|---|---|
| `actions_total` | 407 | Business actions in the catalog, one JSON file each. |
| `status_verified` | 91 | Actions with status `verified`. See AGENT.md for what each status means. |
| `status_observed` | 9 | Actions with status `observed`. See AGENT.md for what each status means. |
| `status_gated` | 87 | Actions with status `gated`. See AGENT.md for what each status means. |
| `status_failed` | 1 | Actions with status `failed`. See AGENT.md for what each status means. |
| `status_seen` | 100 | Actions with status `seen`. See AGENT.md for what each status means. |
| `status_documented` | 119 | Actions with status `documented`. See AGENT.md for what each status means. |
| `verified_writes` | 37 | Verified actions that change data. Each one has a read-back that confirmed the change. |
| `verified_writes_without_read_back` | 0 | Verified writes with no read-back. Must be 0. |
| `requires_confirmation` | 211 | Actions that need the user's OK before they run: sends, deletes and writes that nothing can undo. |
| `live_api_calls` | 639 | Calls made to the live Brevo API. Each is one line in the evidence log. |
| `web_app_actions` | 177 | Business actions found in the web app walk. |
| `web_app_catalog_actions` | 156 | Catalog actions behind the web app actions. One action can serve several buttons. |
| `web_app_actions_with_public_api` | 54 | Web app actions whose catalog action runs through the public API. |
| `corrections` | 37 | Mistakes logged while building the catalog. |
| `corrections_with_check` | 23 | Logged mistakes that name the automated check that now catches them. |
| `lint_errors` | 0 | Errors from the catalog lint. Must be 0. |
<!-- claims:end -->

Each value has a `recompute` command in `catalog/claims.json`. Run it from the repo root to check the value.

## 1. Files

| Path | What it is |
|---|---|
| `catalog/index.json` | One short entry per action: `id`, `label`, `area`, `entity`, `operation_class`, `route_kinds`, `verification`, `free_plan`, `requires_confirmation`. Read this first. |
| `catalog/actions/<id>.json` | The full entry for one action. Valid against `catalog/schema/business_action.schema.json`. |
| `catalog/claims.json` | Every headline number in the write-up, with a `recompute` command. |
| `catalog/coverage.json` | Counts by status, by route and by area, plus the web app walk counts. |
| `catalog/lint.json` | Lint findings. `severity: error` must be empty. `severity: gap` lists missing work. |
| `evidence/runs.jsonl` | One line per live API call and one line per scenario check. The only source of `verified`, `failed` and API-based `gated`. |
| `evidence/ui-walk-*.json`, `sources/ui/ui_map.yaml` | The web app walk, and the join of each web app action to a catalog action. |
| `scenarios/*.yaml` | Live flows: create, read back, update, read back, delete, confirm it is gone. |
| `docs/corrections.jsonl`, `docs/AI_LOG.md` | Every mistake made while building, what caught it, the fix, and the check that now catches it. |
| `tools/mcp_server.py` | MCP server with 3 tools: `find_actions`, `get_action`, `run_action`. |
| `tools/brevo_exec.py` | Executor and verifier. The MCP server calls the same code. |

## 2. Status: how much to trust an action

| `verification.status` | Meaning | What you should do |
|---|---|---|
| `verified` | Ran on a live free account. A write also passed a read-back. A read returned success, and in a scenario it also returned the expected data. | Run it. For a write, still run the read-back in `postcondition` before you report success. |
| `observed` | Done once in the web app, with the app's network calls saved. No public API. | A browser agent can follow `routes[kind=ui_path].ui_steps`. A script cannot run it. |
| `gated` | The free plan refuses it, or it needs a setup step. `verification.notes` holds the exact refusal. | Do not offer it on a free account. Tell the user why. |
| `failed` | Returned success, but the read-back showed no change. `verification.notes` says what fails. | Do not report success from the status code. Run the read-back and report what it shows. |
| `seen` | Seen in the web app, not run. Inputs and exact effect are unknown. | Give the user the UI steps, or hand it to a browser agent. |
| `documented` | Only in the official API spec. Not run with real inputs. `verification.notes` may hold the answer to a call with inputs that could not succeed. | Treat it as untested. Run the read-back after any write. |

## 3. Protocol for one user request

1. Find candidates in `catalog/index.json`, or call `find_actions(request)`.
2. Read the full entry (`get_action(id)`).
3. For each input in `inputs.entity_refs`, get the ID from the `find_with` action. Never guess an ID.
4. If `side_effects.requires_confirmation` is true, ask the user before the call.
5. Run it (`run_action(id, inputs, confirmed)`), or with `tools/brevo_exec.py call <id> '<json inputs>'`.
6. Run the `postcondition.check_with` action and check `postcondition.assert` before you tell the user it is done.

## 4. `run_action` replies

| Reply | Meaning |
|---|---|
| `{"ran": false, "reason": "status is gated: ...", "ui_paths": [...]}` | The status blocks the call. Same for `seen`. |
| `{"ran": false, "reason": "this action has no public API ...", "ui_paths": [...]}` | Only a browser can do it. |
| `{"ran": false, "reason": "the inputs do not match the catalog entry", "errors": [...]}` | Fix the inputs. Each error names the field. |
| `{"ran": false, "reason": "this action needs the user's confirmation ..."}` | Ask the user, then call again with `confirmed=true`. |
| `{"ran": true, "http_status": ..., "response": ..., "catalog_status": ..., "next_step": "..."}` | The call ran. `next_step` is the read-back to do. A `failed` action adds `warning`. |
| `{"ran": "unknown", "reason": "...", "next_step": "..."}` | A write was sent and no usable answer came back. It may have run. Do the `next_step` check before any retry. |
| `{"ran": false, "reason": "the request did not reach Brevo ..."}` | Nothing was sent. Safe to retry. |

`confirmed=true` is your own statement that the user agreed. The server cannot check it. Set it only after the user agreed to this exact call.

MCP client config:

```json
{"mcpServers": {"brevo-catalog": {"command": "<repo>/.venv/bin/python", "args": ["<repo>/tools/mcp_server.py"]}}}
```

The server reads the Brevo API key from `BREVO_API_KEY` or the macOS keychain (`security add-generic-password -s brevo-api-key -a brevo -w`). The key is never in this repository.

## 5. Known Brevo behavior that the spec does not tell you

| Action | What happens | Source |
|---|---|---|
| `brevo.tasks.update_task` | `done: true` returns 204 and sets `DoneAt`, but `get_task` still returns `done: false`. A rename with the same call works. | `verification.notes` of the entry |
| `brevo.deals.create_deal` | Returns 200. The spec says 201. | same |
| `brevo.transactional_emails.get_transac_emails_list` | Needs one of `email`, `messageId`, `templateId`. The spec marks all three optional. The input schema now has this rule. | same |
| `brevo.webhooks.get_webhooks` | Returns 400 "Webhook record does not exist" on an account with no webhooks. | same |
| Reads right after a write | Can miss the change for a few seconds. The scenarios retry a read-back before they fail it. | `scenarios/contacts_lifecycle.yaml` |
| Loyalty actions (`Balance`, `Program`, `Tier`, `Reward`, `Wallet` areas) | 49 of the 50 answer 422 "Invalid loyalty program id" to a fake ID. The free plan cannot create a loyalty program (`brevo.program.create_new_lp` is `gated`), so these cannot run on a free account. | `evidence/runs.jsonl`, `run=probe-gates-*` |

## 6. How to check the submission

1. `jq -c '.claims[] | [.id, .value]' catalog/claims.json` lists every number. Run each `recompute` command to check it. `tests/test_claims.py` runs them all.
2. To trace one status: read `verification.evidence` in the entry (for example `evidence/runs.jsonl#run=contacts-lifecycle-1793639545`), then `grep '"run": "contacts-lifecycle-1793639545"' evidence/runs.jsonl`.
3. To check the build: `.venv/bin/python -m pytest -q`, `.venv/bin/python tools/catalog_lint.py`, `.venv/bin/python tools/presubmit_check.py`. None of them calls Brevo.
4. To check the AI-use record: `docs/AI_LOG.md`. Each entry has what went wrong, who caught it (lint, live verifier, reviewer agent, the agent itself, a human, Brevo) and the check that now catches it.

## 7. Limits you must not infer past

- Free plan only. `gated` means "refused on the free plan", not "does not exist".
- No message reached anyone. Contacts use `@example.com`, campaigns stayed drafts, webhooks point to `example.com`. Actions that send were never run.
- The web app walk did not open every settings section. `evidence/ui-walk-*.json` shows what was opened.
- `find_actions` is keyword matching. Read the entry before you act on the first result.
- A web app action count (`web_app_actions` in `claims.json`) counts buttons. Several buttons can map to one catalog action (`web_app_catalog_actions`).
