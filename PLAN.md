# Plan: an agent-ready catalog of Brevo business actions

## The problem, from the agent's side

An agent that operates Brevo must do five things for every action:

1. Find the right action from a user's intent ("add these people to the newsletter list").
2. Fill the inputs correctly, including IDs of things that exist or that it created earlier.
3. Execute it through the best available route.
4. Know if it worked, from the system's state, not from a 2xx.
5. Know what it cannot undo before it acts.

So the catalog is judged by reliability first and count second. An entry that an agent cannot trust is worse than a missing entry, because the agent will act on it.

## Action format

Each action follows the three layers Monarch publishes (capability, routes, inputs) and adds what an agent needs to trust it:

- **Capability**: product, area, entity, operation class (read, create, update, delete, action), label, and an agent-facing description of when to use it.
- **Routes**, in preference order: documented API, undocumented API (what the web app calls), UI path (steps a browser agent can follow).
- **Inputs**: JSON Schema with types, enums, limits and examples. An input that is the ID of another entity names the action that produces or lists that entity.
- **Outputs**: the response shape, and which field carries the ID of a created entity.
- **Preconditions**: what must be true first (a verified sender, an existing list).
- **Postcondition**: the read action and the assertion that prove the action took effect.
- **Side effects**: reversible or not, the undo action, external effects (sends email or SMS, publishes a page, costs credits), idempotency.
- **Availability**: which plan has it, and whether the free plan can run it.
- **Verification**: status, date and evidence file.

Verification statuses:

| Status | Meaning |
|---|---|
| `verified` | Executed on a live account, postcondition passed. |
| `observed` | Seen working in the web app, with the network call captured, but not replayed by the verifier. |
| `documented` | In the official API spec only. Not executed. |
| `gated` | Exists, but the free plan cannot run it. Evidence is the error or the upgrade prompt. |
| `failed` | Executed and did not behave as documented. The entry says how. |

## Discovery: three sources, cross-checked

1. **The official OpenAPI spec** (`api.brevo.com/v3/swagger_definition_v3.yml`, 292 operations, 35 areas). A deterministic generator turns it into draft entries. This is the coverage baseline, with no LLM involved.
2. **The web app's navigation.** A browser agent walks every menu and screen and lists what a user can click. This finds actions the public API does not have.
3. **The web app's network calls.** While the browser agent performs an action, the network log shows the endpoint the app uses. This gives an undocumented route for UI-only actions.

The difference between sources 2 and 1 is the main finding: what a user can do in Brevo that the public API cannot.

## Verification protocol

- Runs against my own free account only. Every email or SMS goes to my own address or number.
- Each write action runs in a loop: create, read back, assert, update, read back, delete, confirm gone. Fixtures are prefixed `zz-catalog-test-` so cleanup is safe.
- Irreversible external actions (sending a campaign, a transactional email) are run once, to myself, and marked `requires_confirmation: true`.
- Every run writes an evidence file: request, status, response summary, assertion result. No credentials in evidence.
- The verifier is the same code an agent would use to execute, so a verified entry is executable by construction.

## Priorities

1. Free-plan areas a user touches every week: contacts, lists, attributes, segments and folders, email campaigns, templates, senders and domains, transactional email, CRM (companies, deals, tasks, notes), webhooks.
2. UI-only areas that matter for an agent: automations (workflows), forms, landing pages, conversations.
3. Separate or paid products (loyalty programs, wallets, payments, master accounts) are catalogued from the spec as `documented` or `gated`, and not chased further.

## How AI is used

| Step | Who does it | Check |
|---|---|---|
| Spec to draft entries | Deterministic script | Schema validation |
| Agent-facing descriptions, entity names, preconditions | LLM, constrained to the spec text | Schema validation, then review |
| UI walk and network capture | Browser agent (Playwright) | Screenshots and captured requests stored as evidence |
| Execution and verification | Deterministic verifier | Live postcondition |
| Audit | Fresh-context reviewer agent on a sample | Findings logged in `docs/AI_LOG.md` |

`docs/AI_LOG.md` records the tools, the models, and every place where I had to correct the AI.

## Deliverables

- `catalog/actions/*.json`, `catalog/index.json`, and `catalog/schema/business_action.schema.json`.
- `tools/`: generator, verifier and executor.
- `evidence/`: one file per verification run.
- `README.md`: approach, coverage numbers, known gaps, what I would do with more time.

## Assumptions

- Deadline: Monday morning (recruiter's email). The brief says 24 hours, and I asked to confirm.
- Free plan only. Paid-only actions are catalogued, marked `gated`, and not executed.
- No message goes to anyone other than me.
