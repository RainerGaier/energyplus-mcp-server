# Form Fill Demo — Command-Line Guide

Trigger the **Fill Form v0.1** n8n workflow from the command line to fill any catalogued PDF form template with user data from Supabase.

## Prerequisites

1. **curl** installed and on PATH (included with Windows 10+)
2. **Fill Form v0.1** workflow **activated** in n8n (required for production webhook; not needed when using `--test`)
3. At least one form template catalogued in Supabase via the **Add Form Template v0.4** workflow
4. A valid `user_id` in the Supabase `users` table

## Available Form Types

| # | Form Type | Template Ref | Description |
|---|-----------|-------------|-------------|
| 1 | Environmental | ENV-001 | Environmental Permit Application (Part A & F1) |
| 2 | Water | WCN-001 | New Water Connection Application |
| 3 | Planning | APP-001 | Planning Permission Application |
| 4 | Electricity | NEC-001 | New Electricity Connection Application |
| 5 | Effluent | TEF-001 | Trade Effluent Consent Application |
| 6 | Test | TST-001 | Test Electricity Application Form |

## Usage

```
scripts\form-fill-demo.bat [form_type] [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--test` | Use the n8n **test** webhook URL (`webhook-test/fill-form`). Allows debugging in the n8n UI without activating the workflow. |
| `--user UUID` | Override the default user ID. |
| `--project NAME` | Override the project name in the additional data payload. |

### Interactive Mode

Run without arguments to get an interactive menu:

```
scripts\form-fill-demo.bat
```

```
 =============================================
  Form Fill Demo — n8n Webhook Trigger
 =============================================

  Select a form type to fill:

    1. Environmental   (ENV-001)
    2. Water           (WCN-001)
    3. Planning        (APP-001)
    4. Electricity     (NEC-001)
    5. Effluent        (TEF-001)
    6. Test            (TST-001)

    0. Exit

  Enter choice (1-6):
```

### Direct Mode

Pass the form type as the first argument to skip the menu:

```
scripts\form-fill-demo.bat Water
```

### Examples

Fill a Water connection form (production webhook):

```
scripts\form-fill-demo.bat Water
```

Fill an Electricity form using the test webhook (for debugging in n8n UI):

```
scripts\form-fill-demo.bat Electricity --test
```

Fill an Environmental form with a different user:

```
scripts\form-fill-demo.bat Environmental --user a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Fill a Planning form with a custom project name, using test mode:

```
scripts\form-fill-demo.bat Planning --project "Cambridge Data Centre" --test
```

## What Happens

1. The script maps the form type to a `template_ref` (e.g. `Water` → `WCN-001`)
2. Generates a timestamped `run_id` (e.g. `Demo-WCN-001-2026-02-20_14-30`)
3. Sends a `POST` request to the n8n Fill Form webhook with the JSON payload:
   ```json
   {
     "run_id": "Demo-WCN-001-2026-02-20_14-30",
     "template_ref": "WCN-001",
     "user_id": "f24ee278-fb1e-42dc-8777-ac9af1954d25",
     "additional_data": {
       "project_name": "Demo Project",
       "simulation_date": "2026-02-20"
     }
   }
   ```
4. The Fill Form workflow then:
   - Fetches the template record and user data from Supabase
   - Downloads the blank PDF from Supabase storage
   - Maps user data to PDF fields using `source_to_template_mapping`
   - Fills the PDF using the pdf-form-filler node
   - Uploads the filled PDF to Supabase storage (`form_runs/{run_id}/`)
   - Inserts an audit record into `form_run_data`
   - Returns a summary with status, fields filled/missing, and the filled PDF path

## Configuration

Default values are set at the top of `form-fill-demo.bat`:

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_BASE` | `http://localhost:5678` | n8n instance URL |
| `WEBHOOK_PATH` | `webhook/fill-form` | Production webhook path |
| `TEST_PATH` | `webhook-test/fill-form` | Test webhook path |
| `DEFAULT_USER_ID` | `f24ee278-fb1e-...` | Default Supabase user UUID |

Edit these values in the script if your environment differs.

## Webhook URLs

| Mode | URL |
|------|-----|
| Production | `http://localhost:5678/webhook/fill-form` |
| Test | `http://localhost:5678/webhook-test/fill-form` |

**Production** requires the Fill Form v0.1 workflow to be activated in n8n.

**Test** mode (`--test`) works even when the workflow is inactive — n8n will execute it on demand and show results in the UI, which is useful for debugging.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `curl: command not found` | Install curl or ensure it is on your PATH |
| HTTP 404 | Workflow not activated in n8n, or webhook path is incorrect |
| HTTP 500 / error in response | Check the n8n execution log for details |
| `Template not found` | Run Add Form Template v0.4 first to catalogue the PDF |
| `User not found` | Verify the `user_id` exists in the Supabase `users` table |
| Empty fields in filled PDF | Check `source_to_template_mapping` has mapped fields — run Allocate Form Mapping v0.1 to apply overrides |

## Related Workflows

| Workflow | Purpose |
|----------|---------|
| **Add Form Template v0.4** | Catalogue a new PDF template with auto-mapping |
| **Allocate Form Mapping v0.1** | Update field mappings from an edited Excel spreadsheet |
| **Fill Form v0.1** | The sub-workflow called by this script |
| **Form Fill Demo v0.1** | n8n-native version of this demo (manual trigger inside n8n) |
