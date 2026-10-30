# How AI was used, and what I had to fix

Tools: Claude Code (Claude Opus 5.5) as the main agent, with subagents for parallel work and for fresh-context review. Playwright for the browser. Plain Python for everything that must be deterministic.

Rule I followed: the model drafts and explores, and code checks. Nothing enters the catalog as `verified` because a model said so. Only a live call with a passing postcondition sets that status.

## Log

| When | Step | What the AI did | What I checked or fixed |
|---|---|---|---|
| Day 1 | Plan | Drafted the action format from Monarch's published architecture (capability, routes, inputs) | Added postcondition, side effects, availability and verification status, because an agent needs them to trust an action |
| Day 1 | Spec discovery | Found the official OpenAPI spec (`api.brevo.com/v3/swagger_definition_v3.yml`) | Counted it mechanically: 292 operations, 35 areas |
| Day 1 | Generator | Wrote the spec-to-draft generator | Two rules were wrong. (1) The ID builder dropped "to", so `addContactToList` became `add_contact_list`. (2) The "how to find a list" link pointed to "lists in a folder" instead of "all lists", because it took the first match. Fixed both: keep "to", and prefer the route with the fewest path parameters |
| Day 1 | Generator | Named entities from URL paths | Some names are weak (`detail`, `metric`, `request`). They are listed in the known gaps and corrected in `catalog/curation.yaml` for the areas that matter |
