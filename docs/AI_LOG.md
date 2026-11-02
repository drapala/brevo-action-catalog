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
15 corrections: 6 caught by automated checks, 7 by the agent during the session, 1 by a human, 1 by Brevo itself. Open: 0.

| ID | Phase | What went wrong | Caught by | Status | Fix |
|---|---|---|---|---|---|
| C001 | generator | The ID builder dropped the word 'to', so addContactToList became add_contact_list, which reads as 'add a contact list'. | agent self check | fixed, now caught by check L001 | Keep 'to' and 'for' in IDs. Read a sample of generated entries after every generator change. |
| C002 | generator | The hint that tells an agent how to find a list ID pointed to 'Get lists in a folder', which itself needs a folder ID, instead of 'Get all the lists'. The lookup took the first match. | agent self check | fixed, now caught by check L002 | Prefer the route with the fewest path parameters, then the shortest path. |
| C003 | generator | A code formatter split a one-line set over many lines, so a text replacement in the generator silently changed nothing. The regenerated IDs were the same as before. | agent self check | fixed, now caught by check L006 | Edit only after reading the formatted file, and check the generated output after every change. |
| C004 | account setup | The plan assumed an API key on day one. Creating an API key requires a verified phone number. Evidence: `sources/ui/areas-2026-10-30.yaml (Settings, API keys)`. | brevo platform | fixed | Recorded as a precondition of 'Create an API key' and of every send action. The human started phone verification. |
| C005 | account setup | Phone verification by SMS and by call did not work for this account. A request is open with Brevo support. | human | fixed | Verification moved to the routes the web app uses. Actions with only a documented route stay 'documented' until a key exists. |
| C006 | verification design | To test the web app's internal routes from a script, the agent reused the browser's session cookies outside the browser. The web session ended right after. The cause is not confirmed: the session may be bound to the browser that created it. | agent self check | fixed | Never reuse session cookies outside the browser. The exported cookie file was deleted and the human logged in again. |
| C007 | verification design | The agent assumed a fetch from the page's own JavaScript would carry the login. The internal services answered 403 'Cookie auth cookie missing'. | live verifier | fixed | UI-only actions are verified through the UI itself, with the app's own network calls captured as evidence. |
| C008 | presubmit | The secret scanner flagged its own file, because the file holds the patterns it searches for. | agent self check | fixed | The scanner skips its own file. A drift test showed the ledger check fails when the table is stale and passes after a render. |
| C009 | automated check | Check L001 failed on 7 entries, for example: ID drops ['by'] from operationId getExternalFeedByUUID; ID drops ['all'] from operationId getAllExternalFeeds; ID drops ['by'] from operationId getInboundEmailEventsByUuid. | catalog lint | fixed | The ID builder now drops only a, an, the and plural s. 'getScheduledEmailById' becomes get_scheduled_email_by_id. Closed by L001 on the next build. |
| C010 | automated check | Check L002 failed on 14 entries, for example: finder brevo.contacts.get_contact_stats itself needs ['identifier']; finder brevo.conversations.get_automated_message itself needs ['id']; finder brevo.conversations.get_message itself needs ['id']. | catalog lint | fixed | A finder must list the entity without any other ID. When the API has no such route, find_with is empty, so the agent takes the ID from the create response instead of a circular lookup. Closed by L002 on the next build. |
| C011 | automated check | Check V-contacts-lifecycle failed on 1 entries, for example: step list_has_contact (brevo.contacts.get_contacts_from_list): no item with email='zz-catalog-test-1793635604@example.com' in contacts. | live verifier | fixed | Check V-contacts-lifecycle passes again at commit 9b16cb4. |
| C012 | automated check | Check V-crm-lifecycle failed on 1 entries, for example: step read_task_done (brevo.tasks.get_task): done = False, expected True. | live verifier | fixed | Not a code error: Brevo accepts done=true and ignores it (a direct curl and a positive control on name confirmed it). The catalog marks brevo.tasks.update_task as failed with this evidence. The step is now a known_defect, so it is still recorded on every run but no longer reopens this entry. |
| C013 | scenario authoring | The CRM scenario named two action IDs that do not exist in the catalog: the task-types read and the deal-link action. The executor stopped with 'unknown action'. | live verifier | fixed | Every scenario action ID was checked against catalog/index.json. tools/presubmit_check.py now fails on an unknown ID. A negative control with a wrong ID failed as expected. |
| C014 | catalog build | The builder showed brevo.tasks.update_task as verified, because the write returned 204. Its read-back failed, but the failure was filed under the read action (get_task), which had passed in other steps. Evidence: `catalog/actions/brevo.tasks.update_task.json`. | agent self check | fixed | Read-back steps now name the write they check (postcondition_of). A failed read-back marks that write failed. tests/test_postcondition_attribution.py replays the case. |
| C015 | catalog build | The builder marked two list actions failed (get_webhooks, get_transac_emails_list) because a call with no inputs returned 400. Both work with data present or with a filter. The 400 is what an agent gets with no setup, not a broken action. | agent self check | fixed | Both now run in a scenario with setup and are verified. The builder keeps the bare-call error in the entry notes, so an agent knows to pass a filter or to expect 400 on an empty account. |
<!-- corrections:end -->
