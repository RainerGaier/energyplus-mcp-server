# n8n Workflows for EnergyPlus MCP

This folder contains n8n workflow definitions for the EnergyPlus MCP Server.

## Workflows

| Workflow | Purpose | Environment | Status |
|----------|---------|-------------|--------|
| `EnergyPlus Test v0.1.json` | Development/testing with ngrok | Local + ngrok | Legacy |
| `EnergyPlus GCP v1.0.json` | Production on GCP VM (old IP) | GCP VM | Superseded |
| `EnergyPlus v0.3 (WIP).json` | GCP VM with fixed IP | GCP VM | Superseded |
| `EnergyPlus v0.4.json` | Webhook + session support | GCP VM | Superseded |
| `EnergyPlus v0.5.json` | v0.4 + form-filling integration | GCP VM | **Current** |
| `Add_Form-Template v0.2.json` | Upload & catalogue PDF form templates (initial) | Any | Superseded |
| `Add Form Template v0.4.json` | Upload, discover, fuzzy auto-map, Excel export + Supabase upload | Any | Superseded |
| `Add Form Template v0.5.json` | v0.4 + Extended Info Excel for unmapped fields | Any | **Current** |
| `Fill_Form v0.1.json` | Fill PDF forms with user data (sub-workflow) | Any | **Current** |
| `Form Fill Demo v0.1.json` | End-to-end form fill demo (fetch template + user → fill → upload) | Any | **Current** |
| `Allocate Form Mapping v0.1.json` | Download mapping Excel, apply overrides, validate, update Supabase | Any | **Current** |
| `Update Extended Data v0.1.json` | Parse Extended Info Excel, upsert new data keys into user_details | Any | **Current** |
| `Analyse Form Gaps v0.1.json` | Fuzzy-match unmapped PDF fields against all data sources (users, results) | Any | **Current** |
| `Generate Synthetic Data v0.1.json` | Generate synthetic user data for unmapped fields, update mappings + user_details | Any | **Current** |
| `Generate Realistic Data v0.1.json` | Replace "Synthetic ..." placeholders with LLM-generated realistic values | Any | **Current** |

---

## EnergyPlus v0.4 (Current)

**Use when:** Running EnergyPlus MCP on GCP VM with webhook or manual trigger

### What's New in v0.4

| Feature | Description |
|---------|-------------|
| **Dual Trigger** | Manual trigger for testing + Webhook trigger for automation |
| **Session ID** | Unique `session_id` per run for tracking and Supabase folder organization |
| **Analysis Type** | `analysis_type` field (e.g. `Building`, `Wastewater`) for multi-service folder structure |
| **Split Config** | Environment config (static) separated from simulation parameters (per-run) |
| **Conditional Export** | Supabase export controlled by `export.supabase` flag |
| **Nested Folders** | Supabase exports to `{session_id}/{analysis_type}/` path |

### Setup Requirements

1. EnergyPlus MCP container running on GCP VM
2. Port 8081 accessible (firewall rule configured)
3. VM fixed IP: `34.42.239.144`
4. n8n running on port 5678

### Workflow Architecture

```
Manual Trigger ---------> Default Params --------\
                                                   \
                                                    --> Merge Config --> Health Check
                                                   /         |
Webhook Trigger --> Extract Webhook Params -------/          |
                                                             ▼
                                                      Check Services
                                                       /         \
                                                 [healthy]    [fail] → Server Unavailable
                                                     |
                                                     ▼
                                               Fetch Weather → Check Weather
                                                                /         \
                                                          [success]    [fail] → Weather Failed
                                                              |
                                                              ▼
                                                        Generate Model → Check Model
                                                                         /         \
                                                                   [success]    [fail] → Model Failed
                                                                       |
                                                                       ▼
                                                                 Run Simulation → Check Simulation
                                                                                  /         \
                                                                            [success]    [fail] → Sim Failed
                                                                                |
                                                                                ▼
                                                                        Summary Results
                                                                                |
                                                                                ▼
                                                                        Get Full Results
                                                                                |
                                                                                ▼
                                                                       Check Export Flag
                                                                        /             \
                                                                  [true]             [false]
                                                                    |                   |
                                                            Export to Supabase           |
                                                                    |                   |
                                                           Check Supabase Copy          |
                                                            /          \                |
                                                      [success]     [fail]              |
                                                          |            |                |
                                                          |     Supabase Failed         |
                                                          |                             |
                                                          +-------- Final Summary ------+
```

### Configuration

v0.4 splits configuration into two parts:

**Environment Config** (static, inside Merge Config node):
```json
{
  "API_BASE_URL": "http://34.42.239.144:8081",
  "version": "2.0",
  "environment": "gcp_vm"
}
```

**Simulation Parameters** (from trigger - manual defaults or webhook body):
```json
{
  "session_id": "Test_Session-2026-02-06_14-30",
  "analysis_type": "Building",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "location_name": "Cambridge_UK",
  "project_name": "GCP Test Data Center",
  "building_type": "manufacturing",
  "data_center": { "rack_count": 25, "watts_per_rack": 2000 },
  "simulation": { "annual": false, "design_day": true },
  "export": { "supabase": true, "google_drive": false }
}
```

### Supabase Folder Structure

Files are exported to: `{bucket}/{session_id}/{analysis_type}/`

```
bucket/
├── Test_Session-2026-02-06_14-30/
│   └── Building/
│       ├── eplusout.csv
│       ├── eplustbl.htm
│       └── ...
├── My_Real_Project/
│   ├── Building/
│   │   └── <energyplus files>
│   └── Wastewater/
│       └── <qsdsan files>
```

### Using the Webhook

**Production URL:** `POST https://n8n.panicle.org/webhook/energyplus-building`
**Test URL:** `POST https://n8n.panicle.org/webhook-test/energyplus-building`

Send a JSON body with simulation parameters. All fields are optional (defaults are provided):

```bash
curl -X POST https://n8n.panicle.org/webhook/energyplus-building \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "My_Project",
    "analysis_type": "Building",
    "latitude": 52.2053,
    "longitude": 0.1218,
    "location_name": "Cambridge_UK",
    "project_name": "My Data Center",
    "building_type": "manufacturing",
    "data_center": { "rack_count": 25, "watts_per_rack": 2000 },
    "simulation": { "annual": false, "design_day": true },
    "export": { "supabase": true, "google_drive": false }
  }'
```

### Test Scripts

Two test scripts are provided in `scripts/`:

**PowerShell (Windows):**
```powershell
# Interactive menu
.\scripts\test-webhook.ps1

# Test mode (uses n8n test URL)
.\scripts\test-webhook.ps1 -TestMode

# Run specific scenario
.\scripts\test-webhook.ps1 -Scenario 1
```

**Bash (Linux/GCP VM):**
```bash
# Interactive menu
./scripts/test-webhook.sh

# Test mode
./scripts/test-webhook.sh -t

# Run specific scenario
./scripts/test-webhook.sh -s 1
```

**Available scenarios:**

| # | Scenario | Location | Annual | Supabase |
|---|----------|----------|--------|----------|
| 1 | Cambridge UK Data Center | 52.2053, 0.1218 | No | Yes |
| 2 | London Office | 51.5074, -0.1278 | No | Yes |
| 3 | Frankfurt DC | 50.1109, 8.6821 | Yes | No |
| 4 | Cambridge Factory | 52.2053, 0.1218 | No | Yes |
| 5 | Custom JSON | User input | User input | User input |

---

## Legacy Workflows

### EnergyPlus Test v0.1 (Local Development)

**Use when:** Running EnergyPlus MCP locally with ngrok tunnel (legacy)

Requires ngrok tunnel and Google Sheets URL lookup. Superseded by v0.4.

### EnergyPlus GCP v1.0

**Use when:** Reference only (superseded by v0.4)

First GCP VM deployment with hardcoded IP `34.28.104.162`. Superseded by v0.3/v0.4 with updated IP.

### EnergyPlus v0.3 (WIP)

**Use when:** Reference only (superseded by v0.4)

Updated to fixed IP `34.42.239.144`. Manual trigger only, no webhook support.

---

## API Endpoints Used

| Endpoint | Method | Description | Timeout |
|----------|--------|-------------|---------|
| `/health` | GET | Server health check | 10s |
| `/api/weather/fetch` | POST | Download EPW from PVGIS | 60s |
| `/api/models/generate` | POST | Generate IDF from spec | 30s |
| `/api/simulation/run` | POST | Run EnergyPlus | 300s |
| `/api/simulation/results/summary` | GET | Summary results | default |
| `/api/simulation/results` | GET | Full results | default |
| `/api/export/supabase` | POST | Export to Supabase | default |

---

## Importing Workflows

1. Open n8n (`https://n8n.panicle.org`)
2. Click "Add Workflow" > "Import from File"
3. Select `EnergyPlus v0.4.json`
4. Click "Import"
5. Review and save the workflow
6. For webhook: Activate the workflow to enable the webhook endpoint

---

## Testing

### Test Health Check Only

```bash
curl http://34.42.239.144:8081/health
```

### Test Manual Trigger

1. Import v0.4 workflow into n8n
2. Click "Execute Workflow"
3. Monitor each step's output
4. Check Supabase for exported files in `Test_Session-{timestamp}/Building/`

### Test Webhook

1. Activate the workflow in n8n
2. Run test script: `.\scripts\test-webhook.ps1 -TestMode`
3. Select scenario 1 (Cambridge)
4. Monitor execution in n8n
5. Check Supabase folder structure

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Health check fails | Verify container is running: `docker ps \| grep energyplus` |
| Weather fetch timeout | PVGIS API may be slow; increase timeout or retry |
| Simulation fails | Check container logs: `docker logs energyplus-mcp` |
| Supabase export fails | Verify SUPABASE_URL and SUPABASE_KEY in container env |
| Connection refused | Check firewall rules for port 8081 |
| Webhook not responding | Ensure workflow is activated in n8n |
| Missing session_id | Merge Config generates default if not provided |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1 | Jan 2025 | Initial local development version with ngrok |
| v1.0 | Feb 2026 | GCP VM production version (IP: 34.28.104.162) |
| v0.3 | Feb 2026 | Updated to fixed IP 34.42.239.144 |
| v0.4 | Feb 2026 | Dual trigger (manual + webhook), session_id, analysis_type, conditional Supabase export, nested folder structure |
| v0.5 | Feb 2026 | Form-filling integration: user_id, form_templates params, calls Fill Form sub-workflow |
| Add Form Template v0.2 | Feb 2026 | Upload PDF template → Discover Fields → catalogue in Supabase |
| Add Form Template v0.4 | Feb 2026 | Fuzzy auto-mapping (Levenshtein + Jaccard), Excel export with override column, Supabase upload |
| Add Form Template v0.5 | Feb 2026 | v0.4 + Extended Info Excel for unmapped fields (new data keys per user) |
| Fill Form v0.1 | Feb 2026 | Reusable sub-workflow: fetch user data + template mapping → fill PDF → store result |
| Form Fill Demo v0.1 | Feb 2026 | End-to-end demo: fetch template + user → fill PDF → upload + audit |
| Allocate Form Mapping v0.1 | Feb 2026 | Excel-based mapping management: download, parse overrides, validate, update Supabase |
| Update Extended Data v0.1 | Feb 2026 | Parse Extended Info Excel, upsert new data keys into user_details JSONB |
| Analyse Form Gaps v0.1 | Feb 2026 | Fuzzy-match unmapped fields against ~80 reference keys, Excel + JSON gap report |
| Generate Synthetic Data v0.1 | Feb 2026 | Generate synthetic user data for unmapped fields, update mappings + user_details |
| Generate Realistic Data v0.1 | Feb 2026 | Replace "Synthetic ..." placeholders with LLM-generated realistic values (OpenAI GPT-4o) |

---

## Form Handling Workflows (CR-001)

See `roadmap/planning/CR-001-form-handling-integration.md` for full design details.

### Prerequisites

1. **Supabase tables created:** `system_config`, `user_details`, `pdf_ff_templates`, `form_run_data`
2. **n8n-nodes-pdf-form-filler** community node installed in your n8n instance
3. **Supabase API credentials** configured in n8n (service_role key)

### Add Form Template v0.5 (Current)

Uploads a blank PDF form, auto-discovers its fields, applies fuzzy auto-mapping (Levenshtein + Jaccard similarity) against `system_config` user data keys, and generates **two Excel files**:

1. **Mapping Excel** (`{ref}_mapping.xlsx`) — 7-column spreadsheet for reviewing/overriding auto-mappings
2. **Extended Info Excel** (`{ref}_extended_info.xlsx`) — 5-column spreadsheet with only unmapped fields, for defining new data keys and user-specific values

Both files are uploaded to Supabase alongside the template record.

**Trigger:** Manual or `POST /webhook/add-form-template`

**Inputs:** `run_id`, `title`, `description`, PDF binary, optional `template_ref`, `source_site`, `version`

**Flow:**
```
Trigger → Validate → Upload PDF to Bucket → Discover Fields (FF Node)
  → Build Initial Mapping (fuzzy auto-map against system_config keys)
  ├─→ Format Excel Rows (7 cols) → Write Mapping Excel → Upload Mapping Excel ──→ Insert Template Record
  └─→ Filter Unmapped Fields → Format Extended Info Rows (5 cols)                       ↓
       → Write Extended Info Excel → Upload Extended Info Excel              Return Summary
```

**Mapping Excel columns:** PDF Field Name | Field Type | Auto-Mapped (data_key [source]) | Confidence | Score | Manual Override (data_key [source]) | Notes

**Extended Info Excel columns:** PDF Field Name | Field Type | Auto-Mapped (data_key [source]) | Extended data source | Extended data value

**Setup:**
1. Import `Add Form Template v0.5.json` into n8n
2. Configure the Supabase API credential on HTTP nodes
3. For manual testing: attach a PDF binary to the Manual Trigger input

### Fill Form v0.1

Reusable sub-workflow that fills a catalogued PDF template with user data.

**Trigger:** Manual, `POST /webhook/fill-form`, or called as n8n sub-workflow

**Inputs:** `run_id`, `template_ref`, `user_id` (uuid), optional `additional_data`

**Flow:**
```
Trigger → Validate → Fetch Template + Fetch User (parallel)
  → Build Data Payload (merge user fields + additional_data)
  → Download PDF Template from Bucket
  → Fill Form (FF Node, dynamic mode)
  → Upload Filled PDF to Bucket
  → Insert audit record into form_run_data
  → Return Result (includes final_pdf URL)
```

**Setup:**
1. Import `Fill_Form v0.1.json` into n8n
2. Configure Supabase API credentials on all Supabase nodes (3 nodes)
3. Ensure at least one template is catalogued and has mapped fields

### Form Fill Demo v0.1

End-to-end demo workflow that fetches a template and user data from Supabase, builds the data payload, fills the PDF, uploads the result, and records an audit trail.

**Trigger:** Manual or `POST /webhook/form-fill-demo`

**Inputs:** `run_id`, `template_ref`, `user_id`

**Flow:**
```
Trigger → Validate → Fetch Template + Fetch User (parallel)
  → Build Data Payload → Download PDF → Fill Form (FF Node)
  → Upload Filled PDF → Insert Audit Record → Return Summary
```

### Allocate Form Mapping v0.1

Downloads the mapping Excel from Supabase (generated by Add Form Template v0.4), reads user edits from the "Manual Override" column, validates data keys against `system_config`, diffs against existing mapping, and updates the Supabase `source_to_template_mapping` via HTTP PATCH.

**Trigger:** Manual (with `Default Params` node) or `POST /webhook/allocate-form-mapping`

**Inputs:** `template_ref` (which template's mapping to update)

**Flow:**
```
Trigger → Default Params → Download Mapping File (from Supabase)
  → Check Download Result → File Exists?
  → [true] Validate Inputs → Read Excel File → Parse Excel Rows
    → Fetch Valid Data Keys → Merge & Validate → Fetch Existing Mapping
    → Build Update Payload & Audit Diff → Update Template Record → Return Summary
  → [false] File Not Found (returns clean status JSON)
```

**Key feature:** Column F ("Manual Override") takes precedence over Column C ("Auto-Mapped"). Users edit the Excel to override or add mappings, then run this workflow to push changes to Supabase.

### Update Extended Data v0.1

Parses a user-completed Extended Info Excel file from Supabase storage and upserts new data keys into `user_details.details` JSONB for a specific user. Enables form-filling for fields that have no existing user data key.

**Trigger:** Manual (with `Default Params` template_ref + user_id)

**User process:**
1. Download `{template_ref}_extended_info.xlsx` from Supabase (generated by Add Form Template v0.5)
2. Fill column D ("Extended data source") with `new_key [user_details]` or `[user_details]new_key`
3. Fill column E ("Extended data value") with the actual value
4. Upload the edited Excel back to Supabase storage (same path)
5. Run this workflow with `template_ref` and `user_id` in Default Params

**Flow:**
```
Manual Trigger → Default Params → Validate Params
  → Download Extended Info Excel (from Supabase) → Check Download Result
  → Read Excel File → Parse Excel Rows
  → Upsert User Details (RPC) → Return Summary
```

**Key features:**
- Downloads Excel from Supabase storage (no local file access needed)
- Validates UUID format and `[user_details]` source (case-insensitive)
- Supports both `key [source]` and `[source]key` column D formats
- Auto-lowercases data keys
- Uses existing `upsert_user_details` stored procedure (JSONB merge — preserves existing keys)
- Fails fast on parse errors with clear messages

### Analyse Form Gaps v0.1

Automated gap analysis: fuzzy-matches unmapped PDF fields across all (or specific) templates against a reference dictionary of ~80 data keys from users, user_details, and BioSTEAM results. Produces an Excel report and JSON summary.

**Trigger:** Manual (with optional `template_ref` filter)

**Inputs:** `template_ref` (empty = all templates), `min_score` (default 0.70)

**Flow:**
```
Manual Trigger → Default Params
  ├→ Fetch Templates (from Supabase)
  └→ Fetch System Config (user/user_details keys)
       ↓
  Build Reference Dictionary (~80 keys with aliases)
       ↓
  Analyse Gaps (Levenshtein fuzzy matching per unmapped field)
  ├→ Format Excel Rows → Write Excel → Upload to Supabase
  └→ Build JSON Summary
       ↓
  Return Summary (JSON report + Excel binary)
```

**Reference dictionary tiers:**
- **users/user_details** — 13 keys with aliases (first_name, email, postcode, etc.)
- **BioSTEAM results** — capital_costs (TCI, FCI), metrics (IRR, NPV, ROI), operating_costs, tea_configuration, utility_summary, stream_economics, cashflow
- **Run parameters** — 26 BioSTEAM simulation parameters (feedstock_price, enzyme_loading, etc.)
- **Metadata** — run_id, model_id, session_id, etc.

**Excel output (10 columns):** Template Ref | PDF Field Name | Field Type | Current Status | Current Mapping | Suggested Data Key | Suggested Source | Match Score | Match Type | Notes

**Excel upload path:** `gap-reports/{run_id}_gap_report.xlsx`

### Generate Synthetic Data v0.1

Generates synthetic (pseudo-real) user data for unmapped PDF fields, updates template mappings with the new data keys, and upserts the synthetic values into `user_details`. Designed for end-to-end testing of form filling without real data.

**Trigger:** Manual (with `Default Params` template_ref + user_id)

**User process:**
1. Run **Analyse Form Gaps v0.1** to get the gap analysis Excel
2. Add three columns: **Create Data**, **Created** (leave blank — stamped by workflow), **Remove Link** (`TRUE` to unmap a previously mapped field)
   - **Create Data** has three modes: `TRUE` = auto-generate synthetic data, *any other value* = use that value literally as the data, *blank* = skip
3. Upload the edited Excel as `Generate_Data.xlsx` to `PDF-templates/{template_ref}/` in Supabase
4. Run this workflow with `template_ref` and `user_id` in Default Params
5. Re-run safely — rows with `Created=TRUE` are skipped automatically

**Inputs:** `template_ref` (required), `user_id` (defaults to dev user)

**Flow:**
```
Manual Trigger → Default Params → Validate Params
  → Download Generate_Data.xlsx (from Supabase) → Check Download
  → Read Excel File → Filter & Generate Synthetic Data
  → Fetch Existing Mapping → Build Update Payload
  → Update Template Record (PATCH source_to_template_mapping)
  → Upsert User Details (RPC)
  → Format Updated Excel → Write Updated Excel → Upload Updated Excel
  → Return Summary
```

**Key features:**
- Auto-detects Excel columns by keyword (case-insensitive)
- **Auto-generates data keys** from PDF field name when "Suggested Data Key" is empty (e.g., "Report reference number" → `report_reference_number`)
- **Create Data** column supports three modes: `TRUE` (auto-generate), literal value (use as-is), blank (skip)
- Only processes rows with source "users" or "user_details" (skips results)
- **Created column**: Stamped `TRUE` after processing; prevents re-processing on re-run
- **Remove Link column**: Set `TRUE` to unmap a previously mapped field (clears dataKey/source)
- Hardcoded synthetic values for common user fields (Sarah Mitchell, Greenfield Energy Systems Ltd, etc.)
- Unknown keys get fallback: "Synthetic {key name}"
- Updated mappings use confidence: "synthetic", score: 1.0
- Writes updated Excel back to Supabase with Created markers
- Summary includes next-step hint to run Fill Form workflow

**Synthetic data generated:**

| Key | Value |
|-----|-------|
| first_name | Sarah |
| last_name | Mitchell |
| email | sarah.mitchell@greenfield-energy.co.uk |
| phone_number | +44 20 7946 0958 |
| mobile_number | +44 7700 900456 |
| company_name | Greenfield Energy Systems Ltd |
| company_number | 09876543 |
| company_address | Unit 7, Innovation Park, Cambridge, CB1 2QA |
| postcode | CB1 2QA |
| title | Dr |
| position | Principal Process Engineer |
| website | www.greenfield-energy.co.uk |

### Generate Realistic Data v0.1

Replaces "Synthetic ..." placeholder values in `user_details` with contextually appropriate realistic values using an LLM (OpenAI GPT-4o). Designed to run **after** Generate Synthetic Data has created the data structure and mappings.

**Trigger:** Webhook (POST to `/webhook/generate-realistic-data`)

**Prerequisites:**
1. Run **Generate Synthetic Data v0.1** first — this creates the data keys, mappings, and placeholder "Synthetic ..." values
2. `OPENAI_API_KEY` environment variable set on your machine

**Invocation via batch file:**
```cmd
:: Set API key (once, or add to System Environment Variables)
set OPENAI_API_KEY=sk-...

:: Default (TEF-001, test mode)
scripts\generate-realistic-data.bat

:: Custom template + user
scripts\generate-realistic-data.bat WCN-001 f24ee278-fb1e-42dc-8777-ac9af1954d25

:: Production mode (workflow must be activated)
scripts\generate-realistic-data.bat TEF-001 f24ee278-... "UK trade effluent application" prod
```

**Webhook POST body** (sent by the batch file):
```json
{
  "template_ref": "TEF-001",
  "user_id": "f24ee278-...",
  "domain_context": "UK trade effluent discharge consent application...",
  "openai_api_key": "sk-..."
}
```

**Flow:**
```
Webhook Trigger → Validate Params
  → Fetch User Details (Supabase)
  → Fetch Template (Supabase — for PDF field labels)
  → Build LLM Prompt (matches "Synthetic ..." keys to PDF labels)
  → Call OpenAI API (GPT-4o)
  → Format SQL Script (outputs UPDATE statement)
```

**How it works:**
1. Receives API key via webhook POST body (never stored in n8n)
2. Fetches `user_details.details` JSONB and filters keys where the value starts with "Synthetic"
3. Looks up the corresponding PDF field label from `source_to_template_mapping` for each key
4. Builds a prompt asking the LLM to generate realistic values with UK formatting, internal consistency, and domain awareness
5. Calls the OpenAI Chat Completions API (GPT-4o)
6. Parses the JSON response and formats a SQL UPDATE script using `jsonb_build_object` concatenation
7. Returns the SQL script in the webhook response

**Output:** A SQL UPDATE script that you review and run manually. Example:
```sql
UPDATE user_details
SET details = details
  || jsonb_build_object('water_spid', '3 2082 0043 542'::text)
  || jsonb_build_object('daily_volume_of_discharge', '450 m³/day'::text)
  || jsonb_build_object('report_reference_number', 'AW/TE/2026/0847'::text),
    updated_at = now()
WHERE id = 'f24ee278-fb1e-42dc-8777-ac9af1954d25'
  AND details IS NOT NULL;
```

**Key features:**
- **Secure**: API key passed via POST body from environment variable — never stored in n8n workflow
- Domain-aware: the `domain_context` parameter gives the LLM scenario context
- PDF-label-aware: uses `source_to_template_mapping` to provide human-readable field labels
- Safe: outputs SQL for manual review — never writes directly to the database
- Handles markdown-wrapped JSON responses from the LLM
- SQL uses `||` JSONB concatenation to merge without overwriting existing fields
- Batch file supports test mode (default) and production mode

### EnergyPlus v0.5

Extends v0.4 with optional form-filling after simulation. If `user_id` and `form_templates` are provided, calls Fill Form v0.1 for each template after the simulation completes.

**New Input Parameters:**
```json
{
  "user_id": "a1b2c3d4-e5f6-...",
  "form_templates": ["ukpn-g98-application", "pp-app-01"],
  "...all existing v0.4 params..."
}
```

**Additional Flow (after Final Summary):**
```
Final Summary → Check Form Fill (If user_id + templates set)
  → [true] Prepare Form Requests → Call Fill Form webhook (per template)
  → Enhanced Summary (simulation + form results)
  → [false] Enhanced Summary (simulation only)
```
