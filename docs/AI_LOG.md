# How AI was used, and what I had to fix

Tools: Claude Code (Claude Opus 5.5) as the main agent, with subagents for parallel work and for fresh-context review. Playwright for the browser. Plain Python for everything that must be deterministic.

Rule I followed: the model drafts and explores, and code checks. Nothing enters the catalog as `verified` because a model said so. Only a live call with a passing postcondition sets that status.

## Who did what

| Step | AI | Me |
|---|---|---|
| Action format | Drafted it from Monarch's published architecture (capability, routes, inputs) | Added postcondition, side effects, availability and verification status, because an agent needs them to trust an action |
| Spec discovery | Found the official OpenAPI spec and wrote the generator | Checked the counts mechanically (292 operations, 35 areas) and read samples of the output |
| UI walk | Visited every menu area with a browser agent and recorded the buttons and the internal calls | Created the account and handled the steps that need a person (phone, support) |
| Verification | Wrote the executor and the scenarios | Decided what may run on a live account and what must never send to anyone |

## Corrections ledger

Every time something went wrong, it gets a line in `docs/corrections.jsonl` with what happened, what caught it, and the fix. The table below is rendered from that file by `tools/corrections.py render`, and `tools/presubmit_check.py` fails if the two disagree.

<!-- corrections:start -->
8 corrections. Caught by: agent self check 5, brevo platform 1, human 1, live verifier 1. Source of the error: ai generated code 3, brevo platform 2, ai agent 2, tooling 1.

| ID | Phase | What went wrong | Caught by | Fix |
|---|---|---|---|---|
| C001 | generator | The ID builder dropped the word 'to', so addContactToList became add_contact_list, which reads as 'add a contact list'. | agent self check | Keep 'to' and 'for' in IDs. Read a sample of generated entries after every generator change. |
| C002 | generator | The hint that tells an agent how to find a list ID pointed to 'Get lists in a folder', which itself needs a folder ID, instead of 'Get all the lists'. The lookup took the first match. | agent self check | Prefer the route with the fewest path parameters, then the shortest path. |
| C003 | generator | A code formatter split a one-line set over many lines, so a text replacement in the generator silently changed nothing. The regenerated IDs were the same as before. | agent self check | Edit only after reading the formatted file, and check the generated output after every change. |
| C004 | account setup | The plan assumed an API key on day one. Creating an API key requires a verified phone number. Evidence: `sources/ui/areas-2026-10-30.yaml (Settings, API keys)`. | brevo platform | Recorded as a precondition of 'Create an API key' and of every send action. The human started phone verification. |
| C005 | account setup | Phone verification by SMS and by call did not work for this account. A request is open with Brevo support. | human | Verification moved to the routes the web app uses. Actions with only a documented route stay 'documented' until a key exists. |
| C006 | verification design | To test the web app's internal routes from a script, the agent reused the browser's session cookies outside the browser. The web session ended right after. The cause is not confirmed: the session may be bound to the browser that created it. | agent self check | Never reuse session cookies outside the browser. The exported cookie file was deleted and the human logged in again. |
| C007 | verification design | The agent assumed a fetch from the page's own JavaScript would carry the login. The internal services answered 403 'Cookie auth cookie missing'. | live verifier | UI-only actions are verified through the UI itself, with the app's own network calls captured as evidence. |
| C008 | presubmit | The secret scanner flagged its own file, because the file holds the patterns it searches for. | agent self check | The scanner skips its own file. A drift test showed the ledger check fails when the table is stale and passes after a render. |
<!-- corrections:end -->
