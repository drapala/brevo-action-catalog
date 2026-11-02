# Brevo business action catalog

A catalog of 348 Brevo actions that an AI agent can find, fill, run and check. It covers every business action a walk of the web app found on the free plan (106 buttons and menu items, which map to 93 catalog actions), plus the full public API. Each action says how far an agent can trust it, and the trust comes from live calls on a real account, not from the documentation.

| Status | Count | Meaning |
|---|---|---|
| `verified` | 81 | Ran on a live free-plan account, and a read-back (a read made after the call) proved the effect. |
| `observed` | 9 | Done in the web app, with the app's own network calls captured. These actions have no public API. |
| `gated` | 22 | The free plan refuses them, or they need a setup step first. The entry keeps the exact refusal or the screen the app shows. |
| `failed` | 1 | Ran and returned success, but the read-back showed the change did not happen. |
| `seen` | 42 | Seen in the web app (a button or a menu item) and not run. The entry gives the UI steps. These actions have no public API. |
| `documented` | 193 | In the official API spec only. Not run. |

The 81 verified actions include 31 writes (create, update, delete, link). Every write was read back after it ran. The evidence is in `evidence/runs.jsonl` (427 live API calls). Coverage by area is in `catalog/coverage.json`.

## Review in 2 minutes

1. [`demo/agent-demo-2026-11-02.md`](demo/agent-demo-2026-11-02.md): a fresh Claude agent gets four user requests and only the catalog's three MCP tools. Every tool call is in the file, with each reply cut to its first 400 characters.
2. [`catalog/coverage.json`](catalog/coverage.json): the counts in this README, built by `tools/build_catalog.py`.
3. Three entries: a verified write ([`add_contact_to_list`](catalog/actions/brevo.contacts.add_contact_to_list.json)), a failed one ([`update_task`](catalog/actions/brevo.tasks.update_task.json)) and a web-app-only one ([`create_form`](catalog/actions/brevo.forms.create_form.json)).
4. [`docs/AI_LOG.md`](docs/AI_LOG.md): every mistake the AI made while building this, what caught it, and the fix.
5. [`sources/ui/ui_map.yaml`](sources/ui/ui_map.yaml): every action seen in the web app, joined to the catalog.

## Coverage of the web app

The brief asks for everything a user can do by clicking around the product, so the web app is the reference, not the API.

1. A browser agent opened 40 pages from the main menu and the settings menu. 19 of the 25 settings sections were listed but not opened (see the gaps). The deal and task pages showed an onboarding screen, and the Conversations inbox loaded with no control the walk could read. One test item of each kind (list, contact, company, deal, campaign, template) was created first, so that row menus and bulk actions appear. The items were deleted after the walk.
2. It found 106 business actions, plus 15 controls that only change the screen (filters, columns, tabs). The 106 map to 93 catalog actions, because one action can serve several buttons. For example, Rename and Move on a list both call `update_list`.
3. `sources/ui/ui_map.yaml` joins each of the 106 to the catalog. 49 lead to an action an agent can run through the public API. 7 have a captured internal endpoint (method, URL, response), but only a browser agent that follows the UI steps can run them. 6 are blocked on the free plan. The other 44 have UI steps only. Every UI path is also kept on its catalog action as a route.
4. Before this walk, 58 of the 106 matched a catalog action (55%). The walk added 46 new actions for the other 48: 42 `seen` and 4 `gated`. The numbers are in `catalog/coverage.json` under `web_app_walk`, and the raw walk is in `evidence/ui-walk-2026-11-02.json`.

Areas that the free plan blocks, or that need a setup step first, are listed with the screen the app shows instead: deals and tasks (the sales CRM must be turned on first, although the public API creates deals and tasks without that step), custom objects, landing pages, conversions, Analytics studio, loyalty, phone and meetings.

## What the live checks found

These are the reasons a catalog built from the spec alone would mislead an agent.

1. **A success code is not proof.** `brevo.tasks.update_task` answers 204 to `done: true` and sets a completion time, but `get_task` still returns `done: false`. The entry is `failed`, with the evidence.
2. **The spec and the API disagree.** `create_deal` returns 200, where the spec says 201. `get_transac_emails_list` marks every filter optional, but the API rejects a call without `email`, `messageId` or `templateId`. `get_webhooks` returns 400 "Webhook record does not exist" on an account with no webhooks, not an empty list. Each entry keeps this in `verification.notes`, so an agent knows what to send and what to expect. The filter rule is also in the input schema, so the server refuses a call without one of the three.
3. **A read right after a write can miss it.** Once, a contact added to a list was not in the list on the first read. The verifier now retries a read-back a few times before it fails the step. Every later run passed on the first read.
4. **Much of the product has no public API.** Segments (create, delete), forms, and automations exist only in the web app. The catalog has these as `observed` actions with two routes: UI steps for a browser agent, and the internal endpoint the app calls (for example `POST https://forms-api.brevo.com/forms-api/forms`).
5. **The free plan blocks more than the pricing page says.** 16 read calls return 403 or an "upgrade" message (WhatsApp, corporate accounts, consent groups). E-commerce answers "not yet activated": it needs a setup step, which the catalog lists as a precondition. Template folders show an upgrade dialog in the web app.
6. **An API key needs a verified phone.** SMS and call verification failed for this account. Brevo support validated the account on Friday evening, so the live runs started on Monday. The phone check is a precondition of creating an API key and of sending a campaign in the catalog.

## The format

Each action is one JSON file in `catalog/actions/`, valid against `catalog/schema/business_action.schema.json`. It follows Monarch's three layers (capability, routes, inputs) and adds what an agent needs before it acts.

| Field | What it tells the agent |
|---|---|
| `area`, `entity`, `operation_class`, `label`, `description`, `intent_examples` | What the action does, to match it to a user's request. |
| `routes` | How to run it, in order of preference: `documented_api`, `undocumented_api`, `ui_path`. |
| `inputs.schema` | JSON Schema of the inputs. |
| `inputs.entity_refs` | For each input that is an ID: the action that finds it (`find_with`) and the action that creates it (`create_with`). The agent looks IDs up, it does not guess them. |
| `outputs.produces_entity` | Which response field holds the ID of what was created. |
| `postcondition` | The read action and the check that prove the action worked. |
| `side_effects` | Reversible or not, the undo action, external effects (sends email, publishes), idempotency, and `requires_confirmation`. |
| `availability` | Whether the free plan can run it, and the evidence if not. |
| `verification` | Status, date, evidence reference, and notes from the live runs. |

`catalog/index.json` is the short list an agent reads first: id, label, area, entity, operation class, routes, status, free-plan availability and the confirmation flag.

### How an agent uses it

1. Read `catalog/index.json`. Pick candidates by area, entity and label.
2. Open the action file. Prefer `verified`, then `observed`. Treat `documented` as untested. Treat `seen` as a pointer: a browser agent can follow its UI steps, but its inputs and exact effect are not known. Do not offer `gated` actions on a free account.
3. For each ID input, call the `find_with` action first.
4. If `requires_confirmation` is true, ask the user before the call. This covers sends, invitations, deletes, cancels, unlinks, and every write that the catalog cannot undo, such as imports and permission changes (155 actions).
5. Run the action through the MCP server (next section), or with `tools/brevo_exec.py call <action_id> '<json inputs>'` for any `documented_api` route.
6. Run the `postcondition` read and check the effect before telling the user it is done.

## An agent using it

`tools/mcp_server.py` serves the catalog to any MCP client with three tools: `find_actions`, `get_action` and `run_action`. The server applies the catalog's rules on every call:

- The inputs must match the entry's input schema. An unknown input or a missing required one stops the call before it reaches Brevo.
- An action that needs confirmation runs only with `confirmed=true`.
- A `gated` or `seen` action, or one with no public API, does not run. The reply gives the UI steps.
- A `failed` action still runs, and the reply repeats the defect note. Its only member, `update_task`, fails on `done=true` but renames a task correctly.
- A run returns the read-back the agent must do before it reports success, when the entry has one. All 31 verified writes have one. Most `documented` writes do not yet (see the gaps).

`demo/run_agent_demo.py` gave four requests to a fresh Claude agent in headless mode, with only these three tools and no other context. The transcript is in `demo/agent-demo-2026-11-02.md`.

| Request | What the agent did |
|---|---|
| Add a contact to the list named zz-catalog-test-demo-list | It found the list ID with the finder that the entry names, created the contact on that list, and read the contact back before it said done. |
| Mark the task as done | It saw that `update_task` is `failed`, tried once, read the task back, and reported that the task is still open. It also told the user to use the web app, but the catalog has no UI route for completing a task, so that advice had no source. |
| Delete the list | It stopped before the delete and wrote the confirmation question for the user. |
| Create a segment of the contacts who opened last week's campaign | It found no campaigns on the account, saw that segments exist only in the web app, and asked the user what they meant instead of guessing. |

`confirmed=true` is the agent's statement that the user agreed. In the demo the agent also set it on calls that need no confirmation (reads, `create_contact`, `update_task`), where it has no effect. With an MCP client that asks a person before each tool call, a person checks that statement.

## Approach

The full plan is in `PLAN.md`. In short:

1. **Discover from three sources.** The official OpenAPI spec (292 operations) gives a baseline through a deterministic generator. A browser walk of the web app's pages lists what a user can click, and a map joins each click to the catalog. The web app's network log shows the internal endpoint behind a UI-only action. The difference between the UI and the spec is the list of actions with no public API.
2. **Verify on a live account.** Read actions with no required input were probed one by one. Write actions run in scenarios that create, read back, update, read back, delete and confirm the item is gone. The scenarios never send a message to anyone: contacts use `@example.com`, the campaign stays a draft, and the webhook points to `example.com`.
3. **Let only evidence set the status.** `tools/build_catalog.py` sets `verified` only from a passing read-back in `evidence/runs.jsonl`. A failed read-back marks the write that it checks as `failed`, even when the write returned 2xx.

### Priorities

1. The areas a free-plan user touches every week: contacts, lists, attributes, campaigns, templates, transactional email, CRM (companies, deals, tasks, notes) and webhooks. These have the live scenarios.
2. UI-only areas that matter to an agent: segments, forms and automations.
3. Separate or paid products (loyalty, wallets, payments, master accounts) stay `documented` or `gated`. I did not chase them.

I chose depth over count. An entry that an agent trusts but that is wrong is worse than a missing entry, because the agent acts on it.

## How AI was used

The main agent was Claude Code (Claude Opus 5.5). It used subagents for parallel work and for fresh-context review, and Playwright for the browser. Plain Python does every step that must be repeatable: the generator, the executor, the builder and the checks.

The rule: the model drafts and explores, and code checks. No model output can set `verified`.

`docs/AI_LOG.md` has the full record, built from `docs/corrections.jsonl`. It lists 35 corrections: what went wrong, what caught it, and the fix. Examples:

- The ID generator dropped words, so `addContactToList` became `add_contact_list`. Lint check L001 now catches this.
- The builder showed `update_task` as verified, because the failed read-back was filed under the read action. A test now replays this case.
- The agent reused browser cookies outside the browser, and the web session ended. UI-only actions are now done in the browser, and only the network log is read.
- A scenario named action IDs that do not exist. The presubmit check now fails on an unknown ID.
- The first version was built API-first. A check of every requirement in the brief showed that the first walk listed only 24 buttons, and a full walk found that the catalog had only 58 of the 106 web app actions (55%). The full walk and the map above came from that check.

21 of the 35 corrections name the check that now catches the same error: a lint check in `tools/catalog_lint.py`, a live scenario, a test in `tests/`, or `tools/presubmit_check.py`. The other 14 fixed single entries, claims in the write-up, or how the agent worked.

A reviewer agent with no memory of the build tried to complete 8 user requests from the catalog alone, for example "add jane@example.com to the Newsletter list" and "which webhooks do we have?". It found 4 severe problems. Two delete actions did not ask for confirmation. One ID pointed to the wrong finder. Two entries left out facts that an agent needs. I checked each finding against the files, fixed all 4, and logged them (C016 to C019). The minor findings are in the gaps below.

## Assumptions

1. **Deadline.** The brief says 24 hours. The recruiter's email says Monday morning. I worked to Monday and did not ask. Brevo gave the API key only after support validated the phone on Friday evening. All live runs happened on Monday.
2. **Free plan only.** Paid features are catalogued and marked `gated`, not tested.
3. **No message reaches anyone.** Contacts use `@example.com`, campaigns stay drafts, and webhooks point to `example.com`. Actions that send are catalogued but not run.
4. **One business action per user intent.** An API operation and a web app click that do the same thing are one action with two routes. Controls that only change the screen (filters, columns, tabs) are not business actions.
5. **The web app is the reference for coverage.** The API spec is one source of routes, not the definition of what a user can do.

## Known gaps and limits

1. **193 actions are `documented` only.** They come from the spec and were not run. The largest groups are master accounts (22), loyalty balance (18), e-commerce (13) and transactional email (11).
2. **The 46 actions the walk added (42 `seen`, 4 `gated`) were not run.** Only 9 UI-only actions were done end to end with their network calls captured. The walk did not open 19 settings sections (Profile, Language, Individual email, Users, Aura AI control center, Security, Localization, Deliverability Center, UTM parameters, Data feeds, Deals, Campaigns, Inbox, Meetings, Automations, Transactional emails, Transactional SMS, E-commerce, Conversions) or the visual automation editor, and it could not read the deal and task screens (onboarding) or the Conversations inbox.
3. **Request bodies of internal calls are not captured.** The browser log kept headers and responses only. The internal routes give the method, URL and response, but not the body shape.
4. **The executor runs only public API routes.** A script cannot replay the internal routes, because they need the browser's session. A UI-only action needs a browser agent that follows `ui_steps`.
5. **Descriptions of `documented` actions are the spec summaries.** Only the UI-only actions have descriptions written for an agent.
6. **Some inputs still need extra lookups.** 123 ID inputs have no finder, because the API has no plain list route for them. Some list actions cannot filter by name, so an agent must page through results to find "Newsletter".
7. **151 lint gaps remain.** 126 writes have no read-back yet (G001): 82 `documented`, 40 `seen` and 4 `gated`. 25 entity names are weak, for example `detail` (G002). They are listed in `catalog/lint.json`, and `tools/catalog_lint.py` prints the count.
8. **Confirmation is the agent's own flag.** The server holds a confirmation-required action until `confirmed=true`, but it cannot check that a person agreed. An MCP client that asks a person before each tool call closes this. A server-issued token bound to the action and its inputs would also force the agent to show the exact call first. It is not built.
9. **Search is keyword matching.** `find_actions` ranks the right action first for the 15 requests in `tests/test_mcp_server.py`, which include the 4 demo requests word for word. It has no semantic matching, so the agent still reads the entries to choose. On requests outside that set it can rank a wrong action first: "schedule the campaign for tomorrow" puts `delete_email_campaign` first. That action needs confirmation, so it cannot run on a wrong match alone.

## Next steps

1. Run a scenario per remaining free-plan area (SMS templates, senders, files, external feeds), then the paid areas on a trial account.
2. Do each `seen` action once in the browser with a full HAR capture, to turn it into `observed` with the request body and a read-back.
3. Walk the visual automation editor and record steps as actions (add trigger, add email step, activate).
4. Write agent-facing descriptions for the `documented` actions with a model, constrained to the spec text, and check them with a fresh-context reviewer.
5. Re-run all scenarios on a schedule. Brevo changes behavior without notice, and a `verified` status should expire.

## Run it

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv venv && uv pip install -r pyproject.toml pytest
.venv/bin/python tools/gen_from_openapi.py          # spec -> build/openapi_actions
.venv/bin/python tools/build_catalog.py             # build/ + sources/ui_actions + evidence -> catalog/
.venv/bin/python tools/catalog_lint.py              # catalog checks
.venv/bin/python -m pytest -q                       # tests
.venv/bin/python tools/presubmit_check.py           # secrets, schema, ledger, scenario IDs
.venv/bin/python demo/run_agent_demo.py             # needs the claude CLI and a Brevo key
```

Live calls need a Brevo API key. The key is never stored in this repository. Give it in one of two ways:

- the environment variable `BREVO_API_KEY`, or
- the macOS keychain: `security add-generic-password -s brevo-api-key -a brevo -w`

Then:

```bash
.venv/bin/python tools/brevo_exec.py probe-reads
.venv/bin/python tools/brevo_exec.py scenario scenarios/contacts_lifecycle.yaml
```

Scenarios create items with the prefix `zz-catalog-test-` and delete them at the end.

To give the catalog to an MCP client, for example Claude Code or Claude Desktop:

```json
{"mcpServers": {"brevo-catalog": {"command": "<repo>/.venv/bin/python", "args": ["<repo>/tools/mcp_server.py"]}}}
```

## Layout

```
catalog/      actions/*.json, index.json, coverage.json, lint.json, schema/
sources/      openapi/ (spec), ui/ (web app walk and ui_map.yaml), ui_actions/ (UI-only actions)
scenarios/    live create, read, update, delete flows
evidence/     runs.jsonl (every live call), ui-capture-*.json and ui-walk-*.json (browser)
tools/        generator, builder, executor, MCP server, lint, ledger, presubmit
demo/         agent demo runner and its transcript
docs/         AI_LOG.md, corrections.jsonl
tests/        unit tests, many of them replay a past error
```
