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

Parses a user-completed Extended Info Excel file and upserts new data keys into `user_details.details` JSONB for a specific user. Enables form-filling for fields that have no existing user data key.

**Trigger:** Manual (with `Default Params` file path)

**User process:**
1. Download `{template_ref}_extended_info.xlsx` from Supabase (generated by Add Form Template v0.5)
2. Fill column D ("Extended data source") with `new_key [user_details]`
3. Fill column E ("Extended data value") with the actual value
4. Save as `{template_ref}-Extended-info-{user_id}.xlsx` in `~/.n8n-files/`
5. Run this workflow

**Flow:**
```
Manual Trigger → Default Params → Read Binary File → Parse Filename
  → Validate UUID → Read Excel File → Parse Excel Rows
  → Upsert User Details (RPC) → Return Summary
```

**Key features:**
- Extracts `template_ref` and `user_id` from the filename automatically
- Validates UUID format and `[user_details]` source
- Uses existing `upsert_user_details` stored procedure (JSONB merge — preserves existing keys)
- Fails fast on parse errors with clear messages

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
