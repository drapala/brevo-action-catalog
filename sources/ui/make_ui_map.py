"""Writes sources/ui/ui_map.yaml from the 2026-11-02 web app walk (evidence/ui-walk-2026-11-02.json)."""

import yaml

A = "https://app.brevo.com"
L = []
# Use the catalog's area names, so a UI action and its API action group together.
AREA = {
    "Lists": "Contacts",
    "Segments": "Contacts",
    "Contact settings": "Contacts",
    "Email campaigns": "Email Campaigns",
    "Marketing statistics": "Email Campaigns",
    "Templates": "Templates (marketing email)",
}


def add(area, ui, steps, catalog_id=None, kind=None, new=None, **extra):
    line = {"area": AREA.get(area, area), "ui": ui, "steps": steps}
    if kind:
        line["kind"] = kind
    if catalog_id:
        line["catalog_id"] = catalog_id
    if new:
        line["new"] = new
    line.update(extra)
    L.append(line)


def N(id, entity, oc, description, **kw):
    d = {"id": id, "entity": entity, "operation_class": oc, "description": description}
    d.update(kw)
    return d


V = "view"

# Contacts list
P = f"Open {A}/contact/list"
add(
    "Contacts",
    "Create a contact",
    [P, "Click 'Create a contact'", "Fill the email and attributes", "Click 'Create'"],
    "brevo.contacts.create_contact",
)
add(
    "Contacts",
    "Import contacts",
    [
        P,
        "Click 'Import contacts'",
        "Pick 'Import from a file' or 'Copy-paste'",
        "Map the columns and pick a list",
        "Confirm the import",
    ],
    "brevo.contacts.import_contacts",
)
add("Contacts", "Load a list or a segment", [P, "Click 'Load a list or a segment'"], kind=V)
add("Contacts", "Add filter", [P, "Click 'Add filter'"], kind=V)
add("Contacts", "Customize columns", [P, "Click 'Customize columns'"], kind=V)
add(
    "Contacts",
    "Add to a list(s)",
    [P, "Tick the contact rows", "Click 'Add to a list(s)'", "Pick the lists and confirm"],
    "brevo.contacts.add_contact_to_list",
)
add(
    "Contacts",
    "Blocklist",
    [P, "Tick the contact rows", "Click 'Blocklist'", "Confirm"],
    "brevo.contacts.update_contact",
)
add(
    "Contacts",
    "Edit (bulk)",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Edit'", "Set the attribute values and save"],
    "brevo.contacts.update_batch_contacts",
)
add(
    "Contacts",
    "Assign",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Assign'", "Pick a contact owner"],
    new=N(
        "brevo.contacts.assign_contact_owner",
        "contact",
        "update",
        "Set the contact owner (a user of the account) for the selected contacts. The public API has no route for this.",
    ),
)
add(
    "Contacts",
    "Copy SMS number to WhatsApp",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Copy SMS number to WhatsApp'"],
    new=N(
        "brevo.contacts.copy_sms_number_to_whatsapp",
        "contact",
        "update",
        "Copy each selected contact's SMS number into its WhatsApp field. The public API has no route for this; update_batch_contacts can set the WHATSAPP attribute for many contacts at once.",
    ),
)
add(
    "Contacts",
    "Add to automation",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Add to automation'", "Pick an automation"],
    new=N(
        "brevo.automations.add_contacts_to_automation",
        "automation",
        "action",
        "Put the selected contacts into an automation now. The public API can only start an automation through a tracked event.",
        requires_confirmation=True,
    ),
)
add(
    "Contacts",
    "Export",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Export'"],
    "brevo.contacts.request_contact_export",
)
add(
    "Contacts",
    "Delete permanently",
    [P, "Tick the contact rows", "Click 'More actions'", "Click 'Delete permanently'", "Confirm"],
    "brevo.contacts.delete_contact",
)

# Contact page
P = f"Open {A}/contact/index/{{contactId}}"
add(
    "Contacts",
    "Contact page: Add a note",
    [P, "Click 'Add a note'", "Type the note and save"],
    "brevo.notes.create_note",
)
add(
    "Contacts",
    "Contact page: Compose an email",
    [P, "Click 'Compose an email'", "Write and send"],
    new=N(
        "brevo.contacts.send_individual_email",
        "contact",
        "action",
        "Write and send a one-to-one email to this contact from the CRM, from your connected mailbox.",
        external_effect="sends_email",
        requires_confirmation=True,
        reversible=False,
    ),
)
add(
    "Contacts",
    "Contact page: Send an SMS",
    [P, "Click 'Send an SMS'", "Write and send"],
    new=N(
        "brevo.contacts.send_individual_sms",
        "contact",
        "action",
        "Send a one-to-one SMS to this contact. Needs SMS credits.",
        external_effect="sends_sms",
        requires_confirmation=True,
        reversible=False,
    ),
)
add(
    "Contacts",
    "Contact page: Create a task",
    [P, "Click 'Create a task'", "Fill the task and save"],
    "brevo.tasks.create_task",
)
add(
    "Contacts",
    "Contact page: Meeting",
    [P, "Click 'More quick actions'", "Click 'Meeting'"],
    new=N(
        "brevo.meetings.book_meeting_with_contact",
        "meeting",
        "create",
        "Book a meeting with this contact. The Meetings app must be set up first.",
        external_effect="notifies_people",
        requires_confirmation=True,
    ),
    free_plan="limited",
    requires=["Meetings set up"],
)
add(
    "Contacts",
    "Contact page: Deal",
    [P, "Click 'More quick actions'", "Click 'Deal'", "Fill the deal and save"],
    "brevo.deals.create_deal",
)
add(
    "Contacts",
    "Contact page: File",
    [P, "Click 'More quick actions'", "Click 'File'", "Pick a file"],
    "brevo.files.upload_file",
)
add(
    "Contacts",
    "Contact page: Add to automation",
    [P, "Click 'More quick actions'", "Click 'Add to automation'"],
    "brevo.automations.add_contacts_to_automation",
)
add(
    "Contacts",
    "Contact page: Edit preferences",
    [P, "Click 'Edit preferences'", "Change the email and SMS subscriptions"],
    "brevo.contacts.update_contact",
)
add(
    "Contacts",
    "Contact page: Add companies",
    [P, "Click 'Add companies'", "Pick companies"],
    "brevo.companies.link_and_unlink_company_with_contact_and_deal",
)
add(
    "Contacts",
    "Contact page: Add deals",
    [P, "Click 'Add deals'", "Pick deals"],
    "brevo.deals.link_and_unlink_deal_with_contacts_and_companies",
)
add("Contacts", "Contact page: Overview, History, Lists, Preferences tabs", [P, "Click a tab"], kind=V)

# Lists
P = f"Open {A}/contact/list-listing"
add(
    "Lists",
    "Create a list",
    [P, "Click 'Create a list'", "Type the name, pick the folder, click 'Create'"],
    "brevo.contacts.create_list",
)
add("Lists", "Recalculate now", [P, "Click 'Recalculate now'"], kind=V)
add(
    "Lists",
    "List settings",
    [P, "On the list row, click 'more list actions'", "Click 'List settings'"],
    new=N(
        "brevo.contacts.edit_list_settings",
        "list",
        "update",
        "Open the settings of a list in the web app. The fields behind this screen were not captured.",
    ),
)
add(
    "Lists",
    "Duplicate",
    [P, "On the list row, click 'more list actions'", "Click 'Duplicate'"],
    new=N(
        "brevo.contacts.duplicate_list",
        "list",
        "create",
        "Copy a list with its contacts. The public API has no route for this.",
        requires_confirmation=False,
        reversible=True,
    ),
)
add(
    "Lists",
    "Import contacts to the list",
    [P, "On the list row, click 'more list actions'", "Click 'Import contacts to the list'"],
    "brevo.contacts.import_contacts",
)
add(
    "Lists", "Rename", [P, "On the list row, click 'more list actions'", "Click 'Rename'"], "brevo.contacts.update_list"
)
add(
    "Lists",
    "Move",
    [P, "On the list row, click 'more list actions'", "Click 'Move'", "Pick the folder"],
    "brevo.contacts.update_list",
)
add(
    "Lists",
    "Delete list",
    [P, "On the list row, click 'more list actions'", "Click 'Delete list'", "Confirm"],
    "brevo.contacts.delete_list",
)

# Segments
P = f"Open {A}/contact/segment"
add("Segments", "Create a segment", [P, "Click 'Create a segment'"], "brevo.segments.create_segment")
for ui, sid, desc in [
    ("Rename", "rename_segment", "Change the name of a segment."),
    ("Duplicate", "duplicate_segment", "Copy a segment with its rules."),
    ("Move segment", "move_segment", "Move a segment to another segment folder."),
    ("Split into lists", "split_segment_into_lists", "Split the contacts of a segment into several static lists."),
]:
    add(
        "Segments",
        ui,
        [P, "On the segment row, click 'more segment actions'", f"Click '{ui}'"],
        new=N(
            f"brevo.segments.{sid}",
            "segment",
            "create" if ui in ("Duplicate", "Split into lists") else "update",
            desc + " The public API has no route for this.",
        ),
    )
add("Segments", "Refresh data", [P, "On the segment row, click 'more segment actions'", "Click 'Refresh data'"], kind=V)
add(
    "Segments",
    "Delete segment",
    [P, "On the segment row, click 'more segment actions'", "Click 'Delete segment'", "Confirm"],
    "brevo.segments.delete_segment",
)

# Companies
P = f"Open {A}/companies"
add(
    "Companies",
    "Import companies",
    [P, "Click 'Import companies'"],
    "brevo.companies.import_companies_creation_and_updation",
)
add(
    "Companies",
    "Create company",
    [P, "Click 'Create company'", "Fill the fields and save"],
    "brevo.companies.create_company",
)
add("Companies", "Add filter, Customize columns", [P, "Click 'Add filter' or 'Customize columns'"], kind=V)
P = f"Open {A}/companies/detail/{{companyId}}"
add("Companies", "Company page: Add a note", [P, "Click 'Add a note'"], "brevo.notes.create_note")
add("Companies", "Company page: Create a task", [P, "Click 'Create a task'"], "brevo.tasks.create_task")
add("Companies", "Company page: Add a deal", [P, "Click 'Add a deal'"], "brevo.deals.create_deal")
add(
    "Companies",
    "Company page: Compose an email",
    [P, "Click 'Compose an email'"],
    "brevo.contacts.send_individual_email",
)
add(
    "Companies",
    "Company page: Add contacts",
    [P, "Click 'Add contacts'", "Pick contacts"],
    "brevo.companies.link_and_unlink_company_with_contact_and_deal",
)
add(
    "Companies",
    "Create an attribute (companies)",
    [f"Open {A}/companies/settings/company-attributes", "Click 'Create an attribute'"],
    "brevo.companies.create_company_deal_attribute",
)

# Contact settings
P = f"Open {A}/objects/settings/contact"
add("Contact settings", "Create attribute", [P, "Click 'Create attribute'"], "brevo.contacts.create_attribute")
add(
    "Contact settings",
    "Manage attributes visibility, attribute tabs",
    [P, "Click 'Manage attributes visibility' or a tab"],
    kind=V,
)
add(
    "Contact settings",
    "Change contact data settings",
    [
        f"Open {A}/contact/settings",
        "Pick Scores, Last detected location, Unengaged contacts, Apple MPP opens in segments, or Per-contact pixel tracking consent",
    ],
    new=N(
        "brevo.settings.update_contact_data_settings",
        "account_setting",
        "update",
        "Change account-wide contact data settings: scores, last detected location, unengaged contacts, Apple MPP opens in segments, per-contact pixel tracking consent.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
add(
    "Contact settings",
    "Webhooks",
    [f"Open {A}/app-store/webhooks", "Open the 'Webhooks' tab", "Add a webhook"],
    "brevo.webhooks.create_webhook",
)

# Deals, tasks, custom objects
add(
    "Deals",
    "Start for free (activate the sales CRM)",
    [f"Open {A}/crm/deals", "The page redirects to /crm/onboarding", "Click 'Start for free'"],
    new=N(
        "brevo.crm.activate_sales_crm",
        "account_setting",
        "action",
        "Turn on the sales CRM app (deals and tasks screens). Notably, the public API creates deals and tasks without this step; only the web app asks for it.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)

# Email campaigns
P = f"Open {A}/campaigns/listing"
add(
    "Email campaigns",
    "Create folder",
    [P, "Click 'Create folder'"],
    new=N(
        "brevo.email_campaigns.create_campaign_folder",
        "campaign_folder",
        "create",
        "Create a folder to group campaigns. The public API has no route for this.",
    ),
)
add(
    "Email campaigns",
    "Generate campaign with AI",
    [P, "Click 'Generate campaign with AI'"],
    new=N(
        "brevo.email_campaigns.generate_campaign_with_ai",
        "email_campaign",
        "create",
        "Draft a campaign from a prompt with Brevo's AI. The result is a draft; nothing is sent.",
    ),
)
add(
    "Email campaigns",
    "Create campaign",
    [P, "Click 'Create campaign'", "Pick Email", "Type the name and create"],
    "brevo.email_campaigns.create_email_campaign",
)
add("Email campaigns", "Status and tag filters", [P, "Use 'All statuses' or 'Select tags'"], kind=V)
add(
    "Email campaigns",
    "Edit",
    [P, "On the campaign row, click 'Edit draft' or 'Edit'"],
    "brevo.email_campaigns.update_email_campaign",
)
add(
    "Email campaigns",
    "Preview & test",
    [P, "On the campaign row, click 'list-actions'", "Click 'Preview & test'", "Send the test to your own address"],
    "brevo.email_campaigns.send_test_email",
)
add(
    "Email campaigns",
    "Duplicate",
    [P, "On the campaign row, click 'list-actions'", "Click 'Duplicate'"],
    new=N(
        "brevo.email_campaigns.duplicate_campaign",
        "email_campaign",
        "create",
        "Copy a campaign as a new draft. The public API has no route for this.",
        requires_confirmation=False,
        reversible=True,
    ),
)
add(
    "Email campaigns",
    "Add to folder",
    [P, "On the campaign row, click 'list-actions'", "Click 'Add to folder'"],
    new=N(
        "brevo.email_campaigns.add_campaign_to_folder",
        "email_campaign",
        "update",
        "Put a campaign in a campaign folder.",
    ),
)
add(
    "Email campaigns",
    "Assign tag",
    [P, "On the campaign row, click 'list-actions'", "Click 'Assign tag'"],
    "brevo.email_campaigns.update_email_campaign",
)
add(
    "Email campaigns",
    "Resend campaign",
    [P, "On the campaign row, click 'list-actions'", "Click 'Resend campaign'"],
    new=N(
        "brevo.email_campaigns.resend_campaign",
        "email_campaign",
        "action",
        "Send a sent campaign again, for example to contacts who did not open it.",
        external_effect="sends_email",
        requires_confirmation=True,
        reversible=False,
    ),
)
add(
    "Email campaigns",
    "Share template",
    [P, "On the campaign row, click 'list-actions'", "Click 'Share template'"],
    "brevo.email_campaigns.get_shared_template_url",
)
add(
    "Email campaigns",
    "Delete",
    [P, "On the campaign row, click 'list-actions'", "Click 'Delete'", "Confirm"],
    "brevo.email_campaigns.delete_email_campaign",
)
P = f"Open {A}/marketing-campaign/edit/{{campaignId}}"
add(
    "Email campaigns",
    "Editor: rename, sender, recipients, subject, design, settings",
    [P, "Click the edit button of the part to change", "Save"],
    "brevo.email_campaigns.update_email_campaign",
)
add(
    "Email campaigns",
    "Editor: Schedule",
    [P, "Click 'Schedule'", "Pick a date and time"],
    "brevo.email_campaigns.update_email_campaign",
)
add(
    "Email campaigns",
    "Editor: Add languages",
    [P, "Click 'Add languages'"],
    new=N(
        "brevo.email_campaigns.add_campaign_language",
        "email_campaign",
        "update",
        "Add a translated version of the campaign. The public API has no route for this.",
    ),
)
add(
    "Email campaigns",
    "Editor: design actions (reset, view or download HTML, plain text)",
    [P, "Click 'Design actions'"],
    kind=V,
)
add(
    "Marketing statistics",
    "Export (.csv file)",
    [f"Open {A}/marketing-reports/statistics", "Pick the dates", "Click 'Export (.csv file)'"],
    new=N(
        "brevo.marketing_reports.export_statistics_csv",
        "marketing_statistics",
        "read",
        "Download the marketing statistics for a date range as a CSV file.",
    ),
)

# Templates
P = f"Open {A}/templates/listing"
add("Templates", "Create template", [P, "Click 'Create template'"], "brevo.transactional_emails.create_smtp_template")
add("Templates", "Create folder", [P, "Click 'Create folder'"], "brevo.templates.create_template_folder")
add("Templates", "Edit", [P, "On the template row, click 'Edit'"], "brevo.transactional_emails.update_smtp_template")
add(
    "Templates",
    "Preview",
    [P, "On the template row, click 'list-actions'", "Click 'Preview'"],
    "brevo.transactional_emails.post_preview_smtp_email_templates",
)
add(
    "Templates",
    "Duplicate",
    [P, "On the template row, click 'list-actions'", "Click 'Duplicate'"],
    new=N(
        "brevo.templates.duplicate_template",
        "email_template",
        "create",
        "Copy a template. The public API has no route for this; create_smtp_template with the same content does the same.",
        requires_confirmation=False,
        reversible=True,
    ),
)
add(
    "Templates",
    "Activate",
    [P, "On the template row, click 'list-actions'", "Click 'Activate'"],
    "brevo.transactional_emails.update_smtp_template",
)
add(
    "Templates",
    "Generate translation",
    [P, "On the template row, click 'list-actions'", "Click 'Generate translation'"],
    new=N(
        "brevo.templates.generate_translation",
        "email_template",
        "create",
        "Make a translated copy of a template with Brevo's AI.",
    ),
)
add(
    "Templates",
    "Share",
    [P, "On the template row, click 'list-actions'", "Click 'Share'"],
    new=N(
        "brevo.templates.share_template",
        "email_template",
        "read",
        "Get a link that lets another Brevo account import this template.",
    ),
)
add(
    "Templates",
    "Delete",
    [P, "On the template row, click 'list-actions'", "Click 'Delete'", "Confirm"],
    "brevo.transactional_emails.delete_smtp_template",
)

# Forms
P = f"Open {A}/contact/forms-app/subscription"
add("Forms", "Create sign-up form", [P, "Click 'Create sign-up form'"], "brevo.forms.create_form")
add(
    "Forms",
    "Duplicate",
    [P, "On the form row, click 'More Actions'", "Click 'Duplicate'"],
    new=N(
        "brevo.forms.duplicate_form",
        "form",
        "create",
        "Copy a form as a new draft.",
        requires_confirmation=False,
        reversible=True,
    ),
)
add(
    "Forms",
    "Delete",
    [P, "On the form row, click 'More Actions'", "Click 'Delete'", "Confirm with 'Delete form'"],
    "brevo.forms.delete_form",
)
add("Forms", "Sign-up, Unsubscribe, Profile update tabs", [P, "Click a tab"], kind=V)

# Automations
P = f"Open {A}/automation/automations"
add(
    "Automations",
    "Create an automation",
    [P, "Click 'Create an automation'", "Click 'Create from scratch'"],
    "brevo.automations.create_automation",
)
add(
    "Automations",
    "Create from a template",
    [P, "Click 'Create an automation'", "Pick a template, for example 'Welcome message'"],
    new=N(
        "brevo.automations.create_from_template",
        "automation",
        "create",
        "Start an automation from one of 16 templates (welcome message, abandoned cart, anniversary date and others). It starts inactive.",
    ),
)
add(
    "Automations",
    "Generate automation with AI",
    [P, "Click 'Generate automation with AI'"],
    new=N(
        "brevo.automations.generate_with_ai",
        "automation",
        "create",
        "Draft an automation from a prompt with Brevo's AI. It starts inactive.",
    ),
)
add(
    "Automations",
    "Rename",
    [P, "On the automation row, click the actions menu", "Click 'Rename'"],
    "brevo.automations.rename_automation",
)
add(
    "Automations",
    "Duplicate",
    [P, "On the automation row, click the actions menu", "Click 'Duplicate'"],
    new=N(
        "brevo.automations.duplicate_automation",
        "automation",
        "create",
        "Copy an automation. The copy starts inactive.",
        requires_confirmation=False,
        reversible=True,
    ),
)
add(
    "Automations",
    "Assign a tag",
    [P, "On the automation row, click the actions menu", "Click 'Assign a tag'"],
    new=N("brevo.automations.assign_tag", "automation", "update", "Add a tag to an automation to group it."),
)
add(
    "Automations",
    "View report, See details, Access logs",
    [P, "On the automation row, click the actions menu", "Pick the view"],
    kind=V,
)
add(
    "Automations",
    "Delete",
    [P, "On the automation row, click the actions menu", "Click 'Delete'", "Confirm with 'Delete automation'"],
    "brevo.automations.delete_automation",
)
add("Automations", "Workflow logs, Contacts in workflow", [f"Open {A}/automation/logs/scenarios", "Pick a tab"], kind=V)

# Transactional
add(
    "Transactional email",
    "Setup tabs (SMTP, API, Postfix, PHP)",
    [f"Open {A}/transactional/email/real-time", "Pick a tab"],
    kind=V,
)
add(
    "Transactional email",
    "Download CSV of logs",
    [f"Open {A}/transactional/email/logs", "Pick the filters", "Click 'Download CSV'"],
    "brevo.transactional_emails.get_email_event_report",
)
add(
    "Transactional SMS",
    "Download SMS logs",
    [f"Open {A}/transactional/sms/logs", "Click 'Download'"],
    "brevo.transactional_sms.get_sms_events",
)

# Settings
P = f"Open {A}/senders/list"
add("Settings", "Add sender", [P, "Click 'Add sender'"], "brevo.senders.create_sender")
add("Settings", "Edit sender", [P, "On the sender row, click 'Edit'"], "brevo.senders.update_sender")
add(
    "Settings",
    "Delete sender",
    [P, "On the sender row, click 'sender-item-actionList'", "Click 'Delete sender'"],
    "brevo.senders.delete_sender",
)
add(
    "Settings", "Add a domain", [f"Open {A}/senders/domain/list", "Click 'Add a domain'"], "brevo.domains.create_domain"
)
add("Settings", "Dedicated IPs tab", [P, "Click 'Dedicated IPs'"], "brevo.senders.get_ips")
add(
    "Settings",
    "Sending cadence",
    [P, "Click 'Sending cadence'"],
    new=N(
        "brevo.senders.set_sending_cadence",
        "account_setting",
        "update",
        "Limit how many emails the account sends per hour.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
P = f"Open {A}/settings/keys/api"
add(
    "Settings",
    "Generate API key",
    [P, "Click 'Generate API key'", "Type a name, pick the access, click 'Generate'", "Copy the key; it is shown once"],
    new=N(
        "brevo.settings.create_api_key",
        "api_key",
        "create",
        "Create an API key. Needs a verified phone number. Done once in the web app for this project; the network call was not captured.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
for ui, sid, oc in [
    ("Edit API Key", "edit_api_key", "update"),
    ("Deactivate API Key", "deactivate_api_key", "update"),
    ("Delete API Key", "delete_api_key", "delete"),
]:
    add(
        "Settings",
        ui,
        [P, "On the key row, click 'More actions'", f"Click '{ui}'"],
        new=N(
            f"brevo.settings.{sid}",
            "api_key",
            oc,
            f"{ui.split()[0]} an API key. Anything that uses the key stops working if it is deactivated or deleted.",
            external_effect="changes_account",
            requires_confirmation=True,
            reversible=oc != "delete",
        ),
    )
add(
    "Settings",
    "Activate for API keys (authorized IPs)",
    [P, "Click 'Activate for API keys'"],
    new=N(
        "brevo.settings.restrict_api_keys_by_ip",
        "account_setting",
        "update",
        "Allow API calls only from listed IP addresses.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
add(
    "Settings",
    "Generate SMTP key",
    [f"Open {A}/settings/keys/smtp", "Click 'Generate SMTP key'"],
    new=N(
        "brevo.settings.create_smtp_key",
        "smtp_key",
        "create",
        "Create an SMTP key for sending through Brevo's SMTP relay.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
add(
    "Settings",
    "Save time zone",
    [f"Open {A}/settings/advanced", "Pick the time zone", "Click 'Save'"],
    new=N(
        "brevo.settings.update_time_zone",
        "account_setting",
        "update",
        "Change the account time zone used for scheduling and reports.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
)
add(
    "Settings",
    "Definitively close your account",
    [f"Open {A}/settings/advanced", "Click 'Definitively close your account'"],
    new=N(
        "brevo.settings.close_account",
        "account",
        "delete",
        "Close the Brevo account and delete its data. This cannot be undone.",
        external_effect="changes_account",
        requires_confirmation=True,
        reversible=False,
    ),
)

# Library and commerce
P = "Open https://content-library.brevo.com/content-hub"
add("Library", "Add file", [P, "Click 'Add file'"], "brevo.email_campaigns.upload_image_to_gallery")
add(
    "Library",
    "Create folder",
    [P, "Click 'Create folder'"],
    new=N("brevo.library.create_media_folder", "media_folder", "create", "Create a folder in the media library."),
)
add(
    "Library",
    "Generate image",
    [P, "Click 'Generate image'"],
    new=N(
        "brevo.library.generate_image",
        "media_file",
        "create",
        "Make an image with Brevo's AI and save it in the media library.",
    ),
)
add("Library", "Grid or list layout", [P, "Pick a layout"], kind=V)
add(
    "Commerce",
    "Install plugin",
    [f"Open {A}/ecommerce", "Click 'Install plugin'"],
    new=N(
        "brevo.ecommerce.install_store_plugin",
        "integration",
        "action",
        "Connect an online store through a plugin. Until a store is connected, the e-commerce screens stay on setup.",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
    free_plan="limited",
    requires=["an online store"],
)

# Paid or setup walls seen in the menu
add(
    "Landing pages",
    "Landing pages",
    [f"Open {A}/contact/list", "Click 'Landing pages' in the Marketing menu", "The app opens the plans page"],
    new=N(
        "brevo.landing_pages.create_landing_page",
        "landing_page",
        "create",
        "Build and publish a landing page.",
        external_effect="publishes",
        requires_confirmation=True,
    ),
    status="gated",
    free_plan="gated",
    requires=["a paid plan"],
)
add(
    "Analytics",
    "Conversions",
    [f"Open {A}/conversions/listing"],
    new=N(
        "brevo.conversions.create_conversion",
        "conversion",
        "create",
        "Define a conversion to track revenue from campaigns.",
    ),
    status="gated",
    free_plan="gated",
    requires=["a paid plan"],
)
add(
    "Analytics",
    "Analytics studio",
    [f"Open {A}/analytics"],
    new=N("brevo.analytics.open_analytics_studio", "custom_report", "read", "Build custom reports across channels."),
    status="gated",
    free_plan="gated",
    requires=["Professional plan"],
)
add(
    "Phone",
    "Phone",
    [f"Open {A}/phone/onboarding", "Click 'Get package'"],
    new=N(
        "brevo.phone.buy_phone_package",
        "phone_number",
        "action",
        "Buy a phone package to call contacts from Brevo.",
        external_effect="spends_credits",
        requires_confirmation=True,
        reversible=False,
    ),
    status="gated",
    source="sources/ui/areas-2026-10-30.yaml (Phone), the 2026-10-30 walk",
    free_plan="gated",
    requires=["a paid add-on"],
)
add(
    "Meetings",
    "Meetings",
    [f"Open {A}/meetings/offer/all", "The page redirects to /meetings/onboarding"],
    new=N(
        "brevo.meetings.set_up_meetings",
        "meeting",
        "action",
        "Set up the Meetings app (booking pages and calendar link).",
        external_effect="changes_account",
        requires_confirmation=True,
    ),
    free_plan="limited",
    requires=["Meetings set up"],
)
add(
    "Loyalty",
    "Create a loyalty program",
    [f"Open {A}/loyalty", "The free plan shows Upgrade to Enterprise"],
    "brevo.program.create_new_lp",
    status="gated",
)

# The 19 settings sections the first walk only listed, opened read-only on 2026-11-02.
SW = {"evidence": "evidence/ui-walk-settings-2026-11-02.json", "source": "evidence/ui-walk-settings-2026-11-02.json"}
C = "https://conversations-app.brevo.com"


def S(area, ui, steps, catalog_id=None, new=None, **extra):
    add(area, ui, steps, catalog_id, new=new, **SW, **extra)


S("Account", "Update my profile", [f"Open {A}/profile/information", "Edit name, email, phone, company or address", "Save"],
  new=N("brevo.account.update_profile", "account", "update", "Change the account owner's name, email, phone, company and address."))
S("Account", "Set a password", [f"Open {A}/profile/information", "Click the 'Password' tab", "Click 'Set a password'"],
  new=N("brevo.account.set_password", "account", "update", "Set or change the password of the account owner.", requires_confirmation=True))
S("Account", "Change the language", [f"Open {A}/settings/localization", "Pick a language", "Click 'Save the preferences'"],
  new=N("brevo.account.update_language", "account", "update", "Change the language of the Brevo web app."))
S("Users", "Add users", [f"Open {A}/user/member", "Click 'Add users'"], "brevo.user.inviteuser")
S("Users", "Invite a partner user", [f"Open {A}/user/partner", "Click 'Invite your partner user'"],
  new=N("brevo.user.invite_partner_user", "user", "create", "Invite an agency or partner to work in this account.",
        external_effect="sends_email", requires_confirmation=True))
S("Users", "Export the activity log", [f"Open {A}/user/activity-logs", "Click 'Export CSV'"],
  new=N("brevo.user.export_activity_log", "activity_log", "read", "Download the users' activity log as CSV."))
S("Aura", "Turn an Aura agent on or off", [f"Open {A}/aura-settings", "Click the toggle on an agent card (Marketing, Conversations, Data management)"],
  new=N("brevo.aura.toggle_agent", "aura_agent", "update", "Turn one of Brevo's built-in AI agents on or off.", requires_confirmation=True))
S("Aura", "Deactivate Aura", [f"Open {A}/aura-settings", "Click 'Deactivate Aura'"],
  new=N("brevo.aura.deactivate", "aura", "action", "Turn off all of Brevo's built-in AI agents.", requires_confirmation=True))
S("Security", "Turn on two-factor authentication", [f"Open {A}/security/two-factor-authentication", "Click 'Enable two-factor authentication'"],
  new=N("brevo.security.enable_two_factor_auth", "account", "update", "Require a second factor at login.", requires_confirmation=True))
S("Security", "Authorize an IP address", [f"Open {A}/security/authorised_ips", "Click 'Authorize IP addresses'", "Enter the IP"],
  new=N("brevo.security.authorize_ip", "authorized_ip", "create", "Add an IP address to the list allowed to use the account."))
S("Security", "Block unknown IPs for API keys", [f"Open {A}/security/authorised_ips", "Click 'Activate for API keys'"],
  "brevo.settings.restrict_api_keys_by_ip")
S("Security", "Block unknown IPs for SMTP keys", [f"Open {A}/security/authorised_ips", "Click 'Activate for SMTP keys'"],
  new=N("brevo.security.restrict_smtp_keys_by_ip", "smtp_key", "update", "Allow SMTP sending only from authorized IP addresses.", requires_confirmation=True))
S("Security", "Export authorized IPs", [f"Open {A}/security/authorised_ips", "Click 'Export CSV'"],
  new=N("brevo.security.export_authorized_ips", "authorized_ip", "read", "Download the authorized IP addresses as CSV."))
S("Security", "Remove an authorized IP", [f"Open {A}/security/authorised_ips", "Click the delete icon on the IP row", "Confirm"],
  new=N("brevo.security.delete_authorized_ip", "authorized_ip", "delete", "Remove an IP address from the authorized list."))
S("Email Campaigns", "Set up campaign languages", [f"Open {A}/localization", "The free plan shows 'Upgrade to Professional'"],
  new=N("brevo.campaigns.set_up_languages", "campaign_language", "update", "Set the language attribute and the languages for translated campaigns."),
  status="gated", free_plan="gated", requires=["Professional plan"])
S("Email Campaigns", "Create a campaign from the deliverability center", [f"Open {A}/compliance", "Click 'Create campaign'"],
  "brevo.email_campaigns.create_email_campaign")
S("Email Campaigns", "Turn on UTM tracking", [f"Open {A}/global/utms", "Click the 'Activate UTM tracking' toggle"],
  new=N("brevo.campaigns.set_utm_tracking", "utm_setting", "update", "Add UTM parameters to the links in every campaign."))
S("Email Campaigns", "Data feeds", [f"Open {A}/external-feeds/welcome", "The free plan shows 'Upgrade plan'"],
  "brevo.external_feeds.create_external_feed", status="gated")
S("CRM", "Set up deals", [f"Open {A}/crm/settings", "Click 'Start setup'"], "brevo.crm.activate_sales_crm")
S("Email Campaigns", "Change the regional settings", [f"Open {A}/campaign-settings/config", "Set the time zone and the time and date formats", "Click 'Save'"],
  "brevo.settings.update_time_zone")
S("Email Campaigns", "Change the default campaign settings", [f"Open {A}/campaign-settings/config?tab=campaign", "Edit sender, reply-to, header and footer", "Click 'Save'"],
  new=N("brevo.campaigns.update_default_settings", "campaign_setting", "update", "Set the default sender, reply-to address, header and footer for new campaigns."))
S("Email Campaigns", "Change tracking and report settings", [f"Open {A}/campaign-settings/config?tab=tracking", "Set anonymous tracking, image URLs and the CSV separator", "Click 'Save'"],
  new=N("brevo.campaigns.update_tracking_settings", "campaign_setting", "update", "Set how campaign opens and clicks are tracked and how reports export."))
S("Email Campaigns", "Change campaign notifications", [f"Open {A}/campaign-settings/config?tab=notifications", "Set SMS reply forwarding and activity notifications", "Click 'Save'"],
  new=N("brevo.campaigns.update_notification_settings", "campaign_setting", "update", "Choose which campaign notifications the account receives."))
S("Email Campaigns", "Add a test user", [f"Open {A}/campaign-settings/test-list", "Click 'Add test user'"],
  new=N("brevo.campaigns.add_test_user", "test_user", "create", "Add an address to the list that receives test campaigns."))
S("Email Campaigns", "Remove a test user", [f"Open {A}/campaign-settings/test-list", "Click 'Remove' on the test user row"],
  new=N("brevo.campaigns.remove_test_user", "test_user", "delete", "Remove an address from the test list."))
S("Email Campaigns", "Create an unsubscribe page", [f"Open {A}/campaign/pages/unsubscription", "Click 'Create an unsubscription page'"],
  new=N("brevo.campaigns.create_unsubscribe_page", "unsubscribe_page", "create", "Build a custom page that contacts see when they unsubscribe."))
S("Email Campaigns", "Edit an unsubscribe page", [f"Open {A}/campaign/pages/unsubscription", "Click the page row", "Edit and save"],
  new=N("brevo.campaigns.update_unsubscribe_page", "unsubscribe_page", "update", "Change an unsubscribe page."))
S("Email Campaigns", "Duplicate an unsubscribe page", [f"Open {A}/campaign/pages/unsubscription", "Click 'More Actions' on the page row", "Click 'Duplicate'"],
  new=N("brevo.campaigns.duplicate_unsubscribe_page", "unsubscribe_page", "create", "Copy an unsubscribe page."))
S("Contacts", "Add a global computed value", ["Open https://my.brevo.com/lists/global-computed-values", "Click 'Add a New Global Computation Value'"],
  new=N("brevo.contacts.create_global_computed_value", "global_computed_value", "create", "Define a value computed over all contacts, for example the number of readers."))
S("Contacts", "Edit a global computed value", ["Open https://my.brevo.com/lists/global-computed-values", "Click the pencil icon on the value row"],
  new=N("brevo.contacts.update_global_computed_value", "global_computed_value", "update", "Change a global computed value."))
S("Contacts", "Delete a global computed value", ["Open https://my.brevo.com/lists/global-computed-values", "Click the red x on the value row"],
  new=N("brevo.contacts.delete_global_computed_value", "global_computed_value", "delete", "Delete a global computed value."))
S("Webhooks", "Add a webhook from the settings", [f"Open {A}/app-store/webhooks", "Click 'Add webhook'"], "brevo.webhooks.create_webhook")
S("Push", "Set up web push", [f"Open {A}/push-settings", "Click 'Set up Push'"],
  new=N("brevo.push.set_up_push", "push_setting", "action", "Connect a website so it can send push notifications. The settings page showed an error during the walk.", requires_confirmation=True))
S("SMS Campaigns", "Request an SMS sender ID", [f"Open {A}/sms-compliance/listing?source=settings", "Click 'Request Sender ID'"],
  new=N("brevo.sms_campaigns.request_sender_id", "sms_sender", "create", "Ask Brevo to register a sender name for SMS in a country that requires it."))
S("Transactional emails", "Block a contact from transactional email", [f"Open {A}/transactional/email/settings/blocked-contacts", "Click 'Block new contact'"],
  new=N("brevo.transactional_emails.block_contact", "blocked_contact", "create", "Stop transactional emails to one address."))
S("Transactional emails", "Export blocked contacts", [f"Open {A}/transactional/email/settings/blocked-contacts", "Click 'Download CSV'"],
  "brevo.transactional_emails.get_transac_blocked_contacts")
S("Transactional emails", "Block a domain", [f"Open {A}/transactional/email/settings/blocked-domains", "Click 'Add a new domain'"],
  "brevo.transactional_emails.block_new_domain")
S("Transactional emails", "Add a webhook for transactional email", [f"Open {A}/transactional/email/settings", "Click the 'Webhook' card", "Click 'Add webhook'"],
  "brevo.webhooks.create_webhook")
S("Transactional emails", "Change log retention", [f"Open {A}/transactional/email/settings/retention-rules", "Choose the senders and the retention time", "Click 'Save'"],
  new=N("brevo.transactional_emails.update_retention_rules", "retention_rule", "update", "Choose how long transactional email logs and previews are kept.", requires_confirmation=True))
S("Transactional emails", "Change transactional tracking", [f"Open {A}/transactional/email/settings/tracking", "Set anonymous email tracking", "Click 'Save'"],
  new=N("brevo.transactional_emails.update_tracking_settings", "tracking_setting", "update", "Turn anonymous tracking of transactional emails on or off."))
S("Transactional SMS", "Forward SMS replies by email", [f"Open {A}/transactional/sms/settings/configurations", "Choose Yes or No", "Click 'Save'"],
  new=N("brevo.transactional_sms.update_reply_settings", "sms_setting", "update", "Choose whether replies to transactional SMS are forwarded by email."))
S("Transactional SMS", "Change SMS log retention", [f"Open {A}/transactional/sms/settings/retention-rules", "Choose no limit or a limited time", "Click 'Save'"],
  new=N("brevo.transactional_sms.update_retention_rules", "retention_rule", "update", "Choose how long transactional SMS logs are kept.", requires_confirmation=True))
S("Automations", "Turn on the Brevo tracker", [f"Open {A}/automation/advanced", "Click the 'Brevo tracker' card", "Click the 'Identify and track visitors' switch"],
  new=N("brevo.automations.enable_tracker", "tracker", "update", "Track website visitors so automations can react to their visits."))
S("Automations", "Choose how visitors are identified", [f"Open {A}/automation/parameters", "Pick links in emails or a third-party tracker"],
  new=N("brevo.automations.set_visitor_identification", "tracker", "update", "Choose how the tracker links a visitor to a contact."))
S("Automations", "Check the tracker install", [f"Open {A}/automation/parameters", "Click 'Verify'"],
  new=N("brevo.automations.verify_tracker", "tracker", "read", "Check that the tracker code is installed on the website."))
S("E-commerce", "Connect an online store", [f"Open {A}/ecommerce/settings", "Click 'Connect my store'"],
  new=N("brevo.ecommerce.connect_store", "store", "action", "Connect a Shopify, WooCommerce or other store so orders and products sync.", requires_confirmation=True))
S("Meetings", "Set up meetings from the settings", [f"Open {A}/meetings/settings", "Click 'Start setup'"], "brevo.meetings.set_up_meetings")
S("Analytics", "Conversions from the settings", [f"Open {A}/conversions/settings", "The free plan shows 'Upgrade'"], "brevo.conversions.create_conversion", status="gated")
CV = "Conversations"
S(CV, "Connect an individual mailbox", [f"Open {C}/individual-email/settings", "Click 'Connect individual email'"],
  new=N("brevo.conversations.connect_individual_mailbox", "mailbox", "action", "Connect a personal mailbox so its emails show in Brevo.", requires_confirmation=True))
S(CV, "Exclude an email or domain from a mailbox", [f"Open {C}/individual-email/settings", "Click 'Add email or domain'"],
  new=N("brevo.conversations.add_excluded_address", "excluded_address", "create", "Keep emails from an address or domain out of the inbox."))
S(CV, "Install the chat widget", [f"Open {C}/settings/integrations/widget", "Click 'Install chat widget'"],
  new=N("brevo.conversations.install_chat_widget", "chat_widget", "action", "Get the chat widget code for a website."))
S(CV, "Connect a team mailbox", [f"Open {C}/settings/integrations/email", "Click 'Connect team mailbox'"],
  new=N("brevo.conversations.connect_team_mailbox", "mailbox", "action", "Connect a shared mailbox to the team inbox.", requires_confirmation=True))
S(CV, "Connect a Facebook page", [f"Open {C}/settings/integrations/facebook", "Click 'Connect page'"],
  new=N("brevo.conversations.connect_facebook_page", "channel", "action", "Bring Facebook page messages into the inbox. The page also shows 'Get package'.", requires_confirmation=True))
S(CV, "Connect an Instagram account", [f"Open {C}/settings/integrations/instagram", "Click 'Connect account'"],
  new=N("brevo.conversations.connect_instagram", "channel", "action", "Bring Instagram messages into the inbox. The page also shows 'Get package'.", requires_confirmation=True))
S(CV, "Connect a WhatsApp account", [f"Open {C}/settings/integrations/whatsapp", "Click 'Connect account'"],
  new=N("brevo.conversations.connect_whatsapp", "channel", "action", "Bring WhatsApp messages into the inbox. The page also shows 'Get package'.", requires_confirmation=True))
S(CV, "Get an SMS phone number", [f"Open {C}/settings/integrations/sms", "Click 'Get phone number'"],
  new=N("brevo.conversations.get_sms_number", "channel", "action", "Get a phone number for two-way SMS in the inbox.", external_effect="spends_credits", requires_confirmation=True, reversible=False))
S(CV, "Change chat preferences", [f"Open {C}/settings/preferences", "Change languages, visitor IP and location, attachment types or email forwarding"],
  new=N("brevo.conversations.update_chat_preferences", "chat_setting", "update", "Set chat languages, what agents see about visitors, allowed attachments and transcript forwarding."))
S(CV, "Create a saved reply", [f"Open {C}/settings/saved-replies", "Click 'Create saved reply'"],
  new=N("brevo.conversations.create_saved_reply", "saved_reply", "create", "Save a reply that agents can insert in a chat."))
S(CV, "Turn on the AI chatbot", [f"Open {C}/settings/ai-bot", "Click the 'Activate AI chatbot' switch"],
  new=N("brevo.conversations.activate_ai_chatbot", "ai_chatbot", "update", "Let the AI chatbot answer visitors.", requires_confirmation=True))
S(CV, "Configure the AI chatbot", [f"Open {C}/settings/ai-bot", "Edit identity, behavior and handoff settings"],
  new=N("brevo.conversations.configure_ai_chatbot", "ai_chatbot", "update", "Set the chatbot's name, what it helps with, what it avoids, and when it hands off to a person."))
S(CV, "Connect the AI chatbot to a channel", [f"Open {C}/settings/ai-bot", "Click the 'Channels' tab", "Click 'Connect' on a channel"],
  new=N("brevo.conversations.connect_ai_chatbot_channel", "ai_chatbot", "action", "Let the chatbot answer on the chat widget, Facebook, Instagram or WhatsApp.", requires_confirmation=True))
S(CV, "Add an AI chatbot source", [f"Open {C}/settings/ai-bot", "Click the 'Sources' tab", "Click 'Add source'"],
  new=N("brevo.conversations.add_ai_chatbot_source", "ai_chatbot_source", "create", "Give the chatbot a page or document to answer from."))
S(CV, "Turn a chat trigger on or off", [f"Open {C}/settings/actions", "Click the toggle on a trigger"],
  new=N("brevo.conversations.toggle_chat_trigger", "chat_trigger", "update", "Turn an automatic chat message on or off, for example a greeting on the front page."))
S(CV, "Create a chat trigger", [f"Open {C}/settings/actions", "Click 'New trigger'"],
  new=N("brevo.conversations.create_chat_trigger", "chat_trigger", "create", "Create an automatic chat message for a page or a visitor action."))
S(CV, "Configure the contact form", [f"Open {C}/settings/bot", "Set when the bot replies, the form fields and the consent switches"],
  new=N("brevo.conversations.configure_contact_form", "contact_form", "update", "Set the form the chat shows to collect a visitor's details."))
S(CV, "Create a chatbot scenario", [f"Open {C}/settings/scripts", "Click 'New scenario'"],
  new=N("brevo.conversations.create_chatbot_scenario", "chatbot_scenario", "create", "Build a scripted chatbot flow."))
S(CV, "Create an agent group", [f"Open {C}/settings/groups", "Click 'New group'"],
  new=N("brevo.conversations.create_agent_group", "agent_group", "create", "Group agents so chats can be routed to them."))
S(CV, "Turn on assignment rules", [f"Open {C}/settings/assignment-rulesets", "Click the switch"],
  new=N("brevo.conversations.set_assignment_rules", "assignment_rule", "update", "Route chats to agent groups with custom rules."))
S(CV, "Update the chat profile", [f"Open {C}/settings/account", "Edit name, title, photo and status settings"],
  new=N("brevo.conversations.update_chat_profile", "agent_profile", "update", "Change how the agent appears to visitors and when the status goes offline."))
S(CV, "Set chat availability", [f"Open {C}/settings/availability", "Click the switch and set the hours"],
  new=N("brevo.conversations.set_availability", "agent_profile", "update", "Set the hours when the agent is available for chats."))
S(CV, "Change chat notifications", [f"Open {C}/settings/notifications", "Enable desktop notifications, pick a sound, or change the switches"],
  new=N("brevo.conversations.update_notification_settings", "chat_setting", "update", "Choose how the agent is notified of new chats and emails."))


doc = {
    "walked_at": "2026-11-02T17:05:00+00:00",
    "evidence": "evidence/ui-walk-2026-11-02.json",
    "settings_evidence": "evidence/ui-walk-settings-2026-11-02.json",
    "method": "Playwright on the free plan account. One test item of each kind (folder, list, contact, company, deal, campaign, template) was created through the API so that row menus appear, and deleted after the walk.",
    "actions": L,
}
open("sources/ui/ui_map.yaml", "w").write(
    "# Every action seen in the web app on 2026-11-02, joined to the catalog.\n"
    "# catalog_id: the catalog action that does the same thing. new: an action the catalog\n"
    "# did not have, added with status 'seen'. kind view: changes the screen only.\n"
    + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=200)
)
print(len(L), "lines")
