# Brevo business action catalog

A catalog of 348 Brevo actions that an AI agent can find, fill, run and check. It covers everything a user can do by clicking around the web app on the free plan, plus the full public API. Each action says how far an agent can trust it, and the trust comes from live calls on a real account, not from the documentation.

| Status | Count | Meaning |
|---|---|---|
| `verified` | 81 | Ran on a live free-plan account, and a read-back proved the effect. |
| `observed` | 9 | Done in the web app, with the app's own network calls captured. These actions have no public API. |
| `gated` | 21 | The free plan refuses them. The entry keeps the exact refusal or the upgrade screen. |
| `failed` | 1 | Ran, returned success, and did nothing. |
| `seen` | 42 | Seen in the web app (a button or a menu item) and not run. The entry gives the UI steps. These actions have no public API. |
| `documented` | 194 | In the official API spec only. Not run. |

The 81 verified actions include 31 writes (create, update, delete, link). Every write was read back after it ran. The evidence is in `evidence/runs.jsonl` (309 live API calls). Coverage by area is in `catalog/coverage.json`.

## Coverage of the web app

The brief asks for everything a user can do by clicking around the product, so the web app is the reference, not the API.

1. A browser agent opened every page of the main menu and the settings menu (40 pages). One test item of each kind (list, contact, company, deal, campaign, template) was created first, so that row menus and bulk actions appear. The items were deleted after the walk.
2. It found 107 business actions, plus 15 controls that only change the screen (filters, columns, tabs).
3. `sources/ui/ui_map.yaml` joins each of the 107 to the catalog. 61 match an action that has a route an agent can run: 51 through the public API and 10 through the web app's internal calls. Each match also gets the UI steps as a second route.
4. The other 46 have no public API. They are in the catalog as `seen` (42) or `gated` (4), with the UI steps.

Before this walk, the catalog had 61 of the 107 (57%). Now it has all of them. The numbers are in `catalog/coverage.json` under `web_app_walk`, and the raw walk is in `evidence/ui-walk-2026-11-02.json`.

Areas that the free plan blocks, or that need a setup step first, are listed with the screen the app shows instead: deals and tasks (the sales CRM must be turned on first, although the public API creates deals and tasks without that step), custom objects, landing pages, conversions, Analytics studio, loyalty, phone and meetings.

## What the live checks found

These are the reasons a catalog built from the spec alone would mislead an agent.

1. **A success code is not proof.** `brevo.tasks.update_task` answers 204 to `done: true`, but the task stays open. The same call does change the name. The entry is `failed`, with the evidence.
2. **The spec and the API disagree.**
   - `create_deal` returns 200. The spec says 201.
   - `get_transac_emails_list` marks every filter optional. The API rejects a call without `email`, `messageId` or `templateId`.
   - `get_webhooks` returns 400 "Webhook record does not exist" on an account with no webhooks, not an empty list.
   Each entry keeps this in `verification.notes`, so an agent knows what to send and what to expect.
3. **Some writes are eventually consistent.** A contact added to a list appears in the list a few seconds later. The verifier retries the read-back before it fails a step.
4. **Much of the product has no public API.** Segments (create, delete), forms, and automations exist only in the web app. The catalog has these as `observed` actions with two routes: UI steps for a browser agent, and the internal endpoint the app calls (for example `POST https://forms-api.brevo.com/forms-api/forms`).
5. **The free plan blocks more than the pricing page says.** 16 read calls return 403 or an "upgrade" message (WhatsApp, e-commerce, corporate accounts, consent groups). Template folders show an upgrade dialog in the web app.
6. **An API key needs a verified phone.** SMS and call verification failed for this account. Brevo support validated the account on Friday evening, so the live runs started on Monday. The phone check is a precondition in the catalog.

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
4. If `requires_confirmation` is true, ask the user before the call. This covers sends, invitations, deletes, cancels and account settings (111 actions).
5. Run the action: `tools/brevo_exec.py call <action_id> '<json inputs>'` runs any `documented_api` route.
6. Run the `postcondition` read and check the effect before telling the user it is done.

## Approach

The full plan is in `PLAN.md`. In short:

1. **Discover from three sources.** The official OpenAPI spec (292 operations) gives a baseline through a deterministic generator. A browser walk of every page lists what a user can click, and a map joins each click to the catalog. The web app's network log shows the internal endpoint behind a UI-only action. The difference between the UI and the spec is the list of actions with no public API.
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

`docs/AI_LOG.md` has the full record, built from `docs/corrections.jsonl`. It lists 21 corrections: what went wrong, what caught it, and the fix. Examples:

- The ID generator dropped words, so `addContactToList` became `add_contact_list`. Lint check L001 now catches this.
- The builder showed `update_task` as verified, because the failed read-back was filed under the read action. A test now replays this case.
- The agent reused browser cookies outside the browser, and the web session ended. UI-only actions are now done in the browser, and only the network log is read.
- A scenario named action IDs that do not exist. The presubmit check now fails on an unknown ID.
- The first version was built API-first. A check of every requirement in the brief showed that the web app walk was too shallow (57% of the clicks). The full walk and the map above came from that check.

Most corrections led to a check that stops the same error from coming back: lint checks in `tools/catalog_lint.py`, tests in `tests/`, and `tools/presubmit_check.py`.

As a last step, a reviewer agent with no memory of the build tried to complete 8 user requests from the catalog alone, for example "add jane@example.com to the Newsletter list" and "which webhooks do we have?". It found 4 severe problems. Two delete actions did not ask for confirmation. One ID pointed to the wrong finder. Two entries left out facts that an agent needs. I checked each finding against the files, fixed all 4, and logged them (C016 to C019). The minor findings are in the gaps below.

## Assumptions

1. **Deadline.** The brief says 24 hours. The recruiter's email says Monday morning. I worked to Monday and did not ask. Brevo's phone check then held the live runs until Monday.
2. **Free plan only.** Paid features are catalogued and marked `gated`, not tested.
3. **No message reaches anyone.** Contacts use `@example.com`, campaigns stay drafts, and webhooks point to `example.com`. Actions that send are catalogued but not run.
4. **One business action per user intent.** An API operation and a web app click that do the same thing are one action with two routes. Controls that only change the screen (filters, columns, tabs) are not business actions.
5. **The web app is the reference for coverage.** The API spec is one source of routes, not the definition of what a user can do.

## Known gaps and limits

1. **194 actions are `documented` only.** They come from the spec and were not run. The largest groups are master accounts (22), loyalty balance (18), e-commerce (13) and transactional email (11).
2. **46 web app actions are `seen` or `gated`, not run.** Only 9 UI-only actions were done end to end with their network calls captured. The walk also did not open the visual automation editor, the deal and task screens (they need the sales CRM turned on), or the Conversations inbox, which loaded without any control the walk could read.
3. **Request bodies of internal calls are not captured.** The browser log kept headers and responses only. The internal routes give the method, URL and response, but not the body shape.
4. **The executor runs only public API routes.** A script cannot replay the internal routes, because they need the browser's session. A UI-only action needs a browser agent that follows `ui_steps`.
5. **Descriptions of `documented` actions are the spec summaries.** Only the UI-only actions have descriptions written for an agent.
6. **Some inputs still need extra lookups.** 123 ID inputs have no finder, because the API has no plain list route for them. In 93 actions, a deeply nested input schema is cut at depth 6. Some list actions cannot filter by name, so an agent must page through results to find "Newsletter".
7. **101 lint gaps remain.** 76 writes have no postcondition yet (G001), most of them `seen` actions. 25 entity names are weak, for example `detail` (G002). They are listed in `catalog/lint.json`.
8. **Free plan only.** Paid features are listed as `gated`, not tested.

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

## Layout

```
catalog/      actions/*.json, index.json, coverage.json, lint.json, schema/
sources/      openapi/ (spec), ui/ (web app walk and ui_map.yaml), ui_actions/ (UI-only actions)
scenarios/    live create, read, update, delete flows
evidence/     runs.jsonl (every live call), ui-capture-*.json and ui-walk-*.json (browser)
tools/        generator, builder, executor, lint, ledger, presubmit
docs/         AI_LOG.md, corrections.jsonl
tests/        one test per past error
```
