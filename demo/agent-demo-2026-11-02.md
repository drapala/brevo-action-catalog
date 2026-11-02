# Agent demo, 2026-11-02

A fresh Claude agent got each request with only three tools: `find_actions`, `get_action` and `run_action` from `tools/mcp_server.py`. It had no other context. Its instructions:

> You operate the Brevo account of a user through the brevo-catalog tools. Use only these tools. Before you run an action, read its catalog entry with get_action and follow it: look up IDs with the finder it names, respect its verification status and notes, and do the read-back it gives before you report success. The user cannot answer during this session. If an action needs the user's confirmation, do not set confirmed=true; stop and write the question you would ask. Answer in English, in at most six short sentences, and say what you checked.

## 1. "Add zz-catalog-test-demo@example.com to the list named zz-catalog-test-demo-list. Create the contact if it does not exist."

| # | Tool | Input | Reply |
|---|---|---|---|
| 1 | `find_actions` | `{"request": "add a contact to a list by list name, create contact if missing"}` | {"result":[{"id":"brevo.contacts.create_list","label":"Create a list","area":"Contacts","entity":"list","operation_class":"create","route_kinds":["documented_api","ui_path"],"verification":"verified","free_plan":"available","requires_confirmation":false},{"id":"brevo.contacts.add_contact_to_list","label":"Add existing contacts to a list","area":"Contacts","entity":"contact","operation_class":"acti ... |
| 2 | `get_action` | `{"action_id": "brevo.contacts.add_contact_to_list"}` | {"id":"brevo.contacts.add_contact_to_list","product":"brevo","area":"Contacts","entity":"contact","operation_class":"action","label":"Add existing contacts to a list","description":"Add existing contacts to a list","inputs":{"schema":{"type":"object","properties":{"listId":{"format":"int64","type":"integer","description":"Id of the list"},"body":{"oneOf":[{"properties":{"emails":{"description":"(n ... |
| 3 | `get_action` | `{"action_id": "brevo.contacts.get_lists"}` | {"id":"brevo.contacts.get_lists","product":"brevo","area":"Contacts","entity":"list","operation_class":"read","label":"Get all the lists","description":"<Note>Ongoing changes for this endpoint. We're dropping support for the response attributes totalSubscribers and totalBlacklisted. These are non breaking changes. The default value for the attributes will be 0.</Note>","inputs":{"schema":{"type":" ... |
| 4 | `run_action` | `{"action_id": "brevo.contacts.get_lists", "inputs": {"limit": 50, "offset": 0}, "confirmed": true}` | {"ran":true,"http_status":200,"response":{"lists":[{"id":16,"name":"zz-catalog-test-demo-list","folderId":15,"uniqueSubscribers":0,"totalBlacklisted":0,"totalSubscribers":0},{"id":10,"name":"identified_contacts","folderId":9,"uniqueSubscribers":0,"totalBlacklisted":0,"totalSubscribers":0},{"id":2,"name":"Your first list","folderId":1,"uniqueSubscribers":1,"totalBlacklisted":0,"totalSubscribers":0} ... |
| 5 | `find_actions` | `{"request": "get contact details by email"}` | {"result":[{"id":"brevo.contacts.get_contact_info","label":"Get a contact's details","area":"Contacts","entity":"contact","operation_class":"read","route_kinds":["documented_api"],"verification":"verified","free_plan":"available","requires_confirmation":false},{"id":"brevo.transactional_emails.get_transac_blocked_contacts","label":"Get the list of blocked or unsubscribed transactional contacts","a ... |
| 6 | `get_action` | `{"action_id": "brevo.contacts.get_contact_info"}` | {"id":"brevo.contacts.get_contact_info","product":"brevo","area":"Contacts","entity":"contact","operation_class":"read","label":"Get a contact's details","description":"<Note>Follow this format when passing a \"SMS\" phone number as an attribute. Accepted Number Formats 91xxxxxxxxxx +91xxxxxxxxxx 0091xxxxxxxxxx</Note> There are 2 ways to get a contact <br><br> Option 1- https://api.brevo.com/v3/co ... |
| 7 | `run_action` | `{"action_id": "brevo.contacts.get_contact_info", "inputs": {"identifier": "zz-catalog-test-demo@example.com", "identifierType": "email_id"}, "confirmed": true}` | {"ran":true,"http_status":404,"response":{"code":"document_not_found","message":"Contact does not exist"},"catalog_status":"verified"} |
| 8 | `get_action` | `{"action_id": "brevo.contacts.create_contact"}` | {"id":"brevo.contacts.create_contact","product":"brevo","area":"Contacts","entity":"contact","operation_class":"create","label":"Create a contact","description":"<Note>Follow this format when passing a \"SMS\" phone number as an attribute. Accepted Number Formats 91xxxxxxxxxx +91xxxxxxxxxx 0091xxxxxxxxxx</Note> Creates new contacts on Brevo. Contacts can be created by passing either - <br><br> 1.  ... |
| 9 | `run_action` | `{"action_id": "brevo.contacts.create_contact", "inputs": {"email": "zz-catalog-test-demo@example.com", "listIds": [16]}, "confirmed": true}` | {"ran":true,"http_status":201,"response":{"id":7},"catalog_status":"verified","next_step":"Before you report success, run brevo.contacts.get_contact_info and confirm: the entity exists and its fields equal the inputs that were sent"} |
| 10 | `run_action` | `{"action_id": "brevo.contacts.get_contact_info", "inputs": {"identifier": "zz-catalog-test-demo@example.com", "identifierType": "email_id"}, "confirmed": true}` | {"ran":true,"http_status":200,"response":{"id":7,"email":"zz-catalog-test-demo@example.com","emailBlacklisted":false,"smsBlacklisted":false,"whatsappBlacklisted":false,"createdAt":"2026-11-02T18:26:52.542+01:00","modifiedAt":"2026-11-02T18:26:52.542+01:00","listIds":[16],"attributes":{},"subscriptions":{},"statistics":{}},"catalog_status":"verified"} |

**Agent's answer:**

Done. The contact is created and on the list.

What I checked:
1. `get_lists` resolved the name `zz-catalog-test-demo-list` to **list id 16** (3 lists returned, only one name match).
2. `get_contact_info` returned 404 `document_not_found`, so the contact did not exist.
3. `create_contact` with `listIds: [16]` returned 201 and id **7**, which does the create and the list add in one verified call.
4. The catalog read-back (`get_contact_info`) returned 200 with `email: zz-catalog-test-demo@example.com` and `listIds: [16]`.

Both actions are catalog-verified on the documented API and need no confirmation, so I ran them without stopping.

## 2. "Mark the task named zz-catalog-test-demo-task as done."

| # | Tool | Input | Reply |
|---|---|---|---|
| 1 | `find_actions` | `{"request": "mark a task as done / complete a task"}` | {"result":[{"id":"brevo.tasks.update_task","label":"Update a task","area":"Tasks","entity":"task","operation_class":"update","route_kinds":["documented_api"],"verification":"failed","free_plan":"available","requires_confirmation":false},{"id":"brevo.balance.complete_transaction","label":"Complete transaction","area":"Balance","entity":"transaction","operation_class":"action","route_kinds":["docume ... |
| 2 | `get_action` | `{"action_id": "brevo.tasks.update_task"}` | {"id":"brevo.tasks.update_task","product":"brevo","area":"Tasks","entity":"task","operation_class":"update","label":"Update a task","description":"Update an existing CRM task''s properties such as name, type, due date, status, duration, notes, assignee, reminder, or linked entities. Only the fields provided in the request body will be updated; omitted fields remain unchanged.","inputs":{"schema":{ ... |
| 3 | `find_actions` | `{"request": "tasks: list tasks, get task, task status done", "limit": 10}` | {"result":[{"id":"brevo.tasks.get_all_tasks","label":"Get all tasks","area":"Tasks","entity":"task","operation_class":"read","route_kinds":["documented_api"],"verification":"verified","free_plan":"available","requires_confirmation":false},{"id":"brevo.tasks.update_task","label":"Update a task","area":"Tasks","entity":"task","operation_class":"update","route_kinds":["documented_api"],"verification" ... |
| 4 | `get_action` | `{"action_id": "brevo.tasks.get_all_tasks"}` | {"id":"brevo.tasks.get_all_tasks","product":"brevo","area":"Tasks","entity":"task","operation_class":"read","label":"Get all tasks","description":"Retrieve a paginated list of CRM tasks with optional filtering by task type, status, date range, assignee, and linked entities (contacts, deals, companies). Results are sorted by creation date in descending order by default, with a default limit of 50 t ... |
| 5 | `run_action` | `{"action_id": "brevo.tasks.get_all_tasks", "inputs": {"filter[status]": "undone", "limit": 50}}` | {"ran":true,"http_status":200,"response":{"items":[{"id":"6ae8c7b23e949d08d084b96f","taskTypeId":"6ae49ef81b0b941f05d5e6c7","name":"zz-catalog-test-demo-task","companiesIds":[],"contactsIds":[],"assignToId":null,"date":"2030-01-15T10:00:00Z","notes":"","done":false,"createdAt":"2026-11-02T17:26:10.816Z","updatedAt":null,"priority":false}],"pager":{"count":1,"current":1,"from":0,"limit":50,"max":1, ... |
| 6 | `run_action` | `{"action_id": "brevo.tasks.update_task", "inputs": {"id": "6ae8c7b23e949d08d084b96f", "done": true}, "confirmed": true}` | {"ran":true,"http_status":204,"response":null,"catalog_status":"failed","warning":"the call returns success but the read-back check failed: update_task answers 204 to done=true but the task stays not done; the same call does update name","next_step":"Before you report success, run brevo.tasks.get_task and confirm: the entity exists and its fields equal the inputs that were sent"} |
| 7 | `run_action` | `{"action_id": "brevo.tasks.get_task", "inputs": {"id": "6ae8c7b23e949d08d084b96f"}}` | {"ran":true,"http_status":200,"response":{"id":"6ae8c7b23e949d08d084b96f","taskTypeId":"6ae49ef81b0b941f05d5e6c7","name":"zz-catalog-test-demo-task","companiesIds":[],"contactsIds":[],"assignToId":"000000000000000000000000","date":"2030-01-15T10:00:00Z","duration":0,"notes":"","done":false,"reminder":null,"createdAt":"2026-11-02T17:26:10.816Z","updatedAt":null,"DoneAt":"2026-11-02T17:27:34Z","firs ... |

**Agent's answer:**

The task is **not** marked done. Report:

- I found the task with `get_all_tasks`: `zz-catalog-test-demo-task`, id `6ae8c7b23e949d08d084b96f`, `done: false`.
- The catalog entry for `brevo.tasks.update_task` carries verification status `failed` with the note that it answers 204 to `done=true` but the task stays not done.
- I sent the documented `PATCH /v3/crm/tasks/{id}` with `done: true` and got 204.
- The required read-back (`get_task`) still shows `done: false`; only `DoneAt: 2026-11-02T17:27:34Z` was set, so the flag itself did not flip.
- The catalog lists no other write route for task status, so this is a confirmed Brevo API defect, not an input error on my side.
- Marking it done needs the Brevo CRM web UI; no API-only path exists today.

## 3. "Delete the contact list named zz-catalog-test-demo-list."

| # | Tool | Input | Reply |
|---|---|---|---|
| 1 | `find_actions` | `{"request": "delete a contact list by name"}` | {"result":[{"id":"brevo.contacts.delete_folder","label":"Delete a folder (and all its lists)","area":"Contacts","entity":"folder","operation_class":"delete","route_kinds":["documented_api"],"verification":"verified","free_plan":"available","requires_confirmation":true},{"id":"brevo.contacts.delete_list","label":"Delete a list","area":"Contacts","entity":"list","operation_class":"delete","route_kin ... |
| 2 | `get_action` | `{"action_id": "brevo.contacts.delete_list"}` | {"id":"brevo.contacts.delete_list","product":"brevo","area":"Contacts","entity":"list","operation_class":"delete","label":"Delete a list","description":"Permanently delete a contact list identified by its ID. The contacts in the list are not deleted; they are only removed from this list. Returns a 404 error if the list ID does not exist.","inputs":{"schema":{"type":"object","properties":{"listId": ... |
| 3 | `get_action` | `{"action_id": "brevo.contacts.get_lists"}` | {"id":"brevo.contacts.get_lists","product":"brevo","area":"Contacts","entity":"list","operation_class":"read","label":"Get all the lists","description":"<Note>Ongoing changes for this endpoint. We're dropping support for the response attributes totalSubscribers and totalBlacklisted. These are non breaking changes. The default value for the attributes will be 0.</Note>","inputs":{"schema":{"type":" ... |
| 4 | `run_action` | `{"action_id": "brevo.contacts.get_lists", "inputs": {"limit": 50, "offset": 0, "sort": "desc"}}` | {"ran":true,"http_status":200,"response":{"lists":[{"id":16,"name":"zz-catalog-test-demo-list","folderId":15,"uniqueSubscribers":1,"totalBlacklisted":0,"totalSubscribers":0},{"id":10,"name":"identified_contacts","folderId":9,"uniqueSubscribers":0,"totalBlacklisted":0,"totalSubscribers":0},{"id":2,"name":"Your first list","folderId":1,"uniqueSubscribers":1,"totalBlacklisted":0,"totalSubscribers":0} ... |

**Agent's answer:**

I stopped before deleting — this action is flagged irreversible and needs your confirmation, which you cannot give in this session.

What I checked:
- `brevo.contacts.delete_list` catalog entry: verified, documented API `DELETE /v3/contacts/lists/{listId}`, `reversible: false`, `requires_confirmation: true`, no undo action.
- Resolved the name via the named finder `brevo.contacts.get_lists`: exactly one match, **id 16**, `zz-catalog-test-demo-list`, folder 15, 1 unique subscriber. No ambiguity.

My question for you: confirm I should permanently delete list id 16 (`zz-catalog-test-demo-list`)? The contacts themselves survive and are only unlinked, but the list and its membership cannot be restored. Once you confirm, I will run the delete and then the read-back (`brevo.contacts.get_list` on 16 must return 404).

## 4. "Create a segment of the contacts who opened last week's campaign."

| # | Tool | Input | Reply |
|---|---|---|---|
| 1 | `find_actions` | `{"request": "create a contact segment / list based on filter criteria"}` | {"result":[{"id":"brevo.contacts.create_list","label":"Create a list","area":"Contacts","entity":"list","operation_class":"create","route_kinds":["documented_api","ui_path"],"verification":"verified","free_plan":"available","requires_confirmation":false},{"id":"brevo.contacts.create_folder","label":"Create a folder","area":"Contacts","entity":"folder","operation_class":"create","route_kinds":["doc ... |
| 2 | `find_actions` | `{"request": "campaign report: contacts who opened an email campaign"}` | {"result":[{"id":"brevo.contacts.get_contact_stats","label":"Get email campaigns' statistics for a contact","area":"Contacts","entity":"campaign_stat","operation_class":"read","route_kinds":["documented_api"],"verification":"documented","free_plan":"unknown","requires_confirmation":false},{"id":"brevo.email_campaigns.get_email_campaign","label":"Get an email campaign report","area":"Email Campaign ... |
| 3 | `get_action` | `{"action_id": "brevo.segments.create_segment"}` | {"id":"brevo.segments.create_segment","product":"brevo","area":"Contacts","entity":"segment","operation_class":"create","label":"Create a segment","description":"Save a segment: a set of contacts that match rules, kept up to date by Brevo. The public API has no route for this. The rules are set in the web app's filter editor. This entry does not define the rule format, because the request body was ... |
| 4 | `get_action` | `{"action_id": "brevo.email_campaigns.get_email_campaigns"}` | {"id":"brevo.email_campaigns.get_email_campaigns","product":"brevo","area":"Email Campaigns","entity":"email_campaign","operation_class":"read","label":"Return all your created email campaigns","description":"<Note>The response payload for this endpoint has changed You now need to specify which type of statistics you would like to retrieve. For more information visit [this page](https://developers ... |
| 5 | `run_action` | `{"action_id": "brevo.email_campaigns.get_email_campaigns", "inputs": {"status": "sent", "startDate": "2026-10-26T00:00:00.000Z", "endDate": "2026-11-02T00:00:00.000Z", "excludeHtmlContent": true, "lim ...` | {"ran":true,"http_status":200,"response":{"campaigns":[],"count":0},"catalog_status":"verified"} |
| 6 | `run_action` | `{"action_id": "brevo.email_campaigns.get_email_campaigns", "inputs": {"status": "sent", "excludeHtmlContent": true, "limit": 20, "sort": "desc"}}` | {"ran":true,"http_status":200,"response":{"campaigns":[],"count":0},"catalog_status":"verified"} |
| 7 | `run_action` | `{"action_id": "brevo.email_campaigns.get_email_campaigns", "inputs": {"excludeHtmlContent": true, "limit": 20, "sort": "desc"}}` | {"ran":true,"http_status":200,"response":{"campaigns":[],"count":0},"catalog_status":"verified"} |

**Agent's answer:**

I did not create anything — the request is blocked twice over.

**Check 1 — no campaign to anchor on.** `brevo.email_campaigns.get_email_campaigns` returned HTTP 200 with `count: 0` both for 2026-10-26→11-02 and unfiltered with no status filter, so the success path is confirmed and this account holds no email campaign whose opens I could read.

**Check 2 — segment creation is not an API action here.** The catalog entry for `brevo.segments.create_segment` has no public API route (status `observed`, UI steps only), the rule body was never captured, and it states plainly that a rule-based segment must not be built without a browser agent following those steps; I hold only the brevo-catalog tools, so I cannot drive the web app.

**My question for you:** which account or campaign did you mean, given this API key sees zero campaigns — a different sending account, or an SMS/automation rather than an email campaign? Tell me that, and whether you want the click-by-click filter steps for the segment editor, and I will continue.

