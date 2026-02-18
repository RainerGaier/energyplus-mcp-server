# CR-001: Form Handling & User Data Integration

**Status:** Implemented — 2026-02-17
**Author:** Rainer Gaier
**Date:** 2026-02-16 (rev 2)
**Branch:** `form_handling` (EP project)
**Reviewer(s):** Rob (database schema), Rainer (workflows & code)

---

## 1. Context & Motivation

The "Stakeholder-Informed Rapid Site Selection & Technical Modelling" system (see `docs/ARCHITECTURE.md` §1.2) currently operates as a simulation pipeline with no persistent user data model and no automated form-filling capability.

Many workflows in the system require PDF forms to be submitted to external bodies (e.g. planning permission applications, grid connection requests, environmental assessments). Today these are filled manually — a repetitive, error-prone process.

This CR introduces:
1. A **user data model** in Supabase (extending the existing `users` table with configurable detail fields)
2. A **PDF template catalogue** with auto-discovered form fields
3. **Automated form-filling workflows** that map user data → PDF fields
4. A **form run audit trail** for compliance and traceability

The implementation leverages the existing **n8n-nodes-pdf-form-filler** (FF project) node which provides `Discover Fields` and `Fill Form` operations.

---

## 2. Scope

### 2.1 In Scope

| Item | Project | Description |
|------|---------|-------------|
| New Supabase tables (4) | EP | `system_config`, `user_details`, `pdf_ff_templates`, `form_run_data` |
| Workflow: Add Form Template v0.1 | EP | Upload PDF → catalogue → discover fields |
| Workflow: Fill Form v0.1 | EP | Map user data → fill PDF → store result |
| Workflow: EnergyPlus v0.5 | EP | Extend v0.4 with form-filling integration point |
| Database schema document | EP | Standalone file for Rob to review/implement |

### 2.2 Out of Scope (This CR)

- ~~Automated field-name-to-data mapping (AI/fuzzy matching) — noted as future enhancement~~ → Implemented in Phase 5 (v0.3 fuzzy auto-mapping)
- Changes to the FF project codebase (node itself is stable at v0.1.0)
- n8n Cloud deployment considerations
- Authentication/authorization for Supabase API access

### 2.3 Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| n8n-nodes-pdf-form-filler v0.1.0 | Deployed | Must be installed in n8n instance |
| Supabase project `egrzvwnjrtpwwmqzimff` | Active | Currently used for file storage only |
| Supabase bucket `panicleDevelop_1` | Active | Will store PDF templates and filled PDFs |
| n8n instance at `n8n.panicle.org` | Active | Hosts all workflows |

---

## 3. Database Schema Design

> **Standalone schema file:** `roadmap/planning/CR-001-database-schema.sql`
> (For Rob to review and implement)

### 3.1 Table: `system_config`

**Purpose:** Global key-value configuration store for system-wide parameters that affect multiple workflows. Provides a single source of truth for data definitions like "what additional fields to collect for a user."

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `serial` | PK | Auto-increment ID |
| `parameter` | `text` | UNIQUE, NOT NULL | Configuration key (e.g. `user_details`) |
| `setting` | `jsonb` | NOT NULL | Configuration value — structure varies by parameter |
| `description` | `text` | | Human-readable explanation of what this parameter controls |
| `created_at` | `timestamptz` | DEFAULT now() | Record creation timestamp |
| `updated_at` | `timestamptz` | DEFAULT now() | Last modification timestamp |

**Seed data example:**

The `user_details` config mirrors the columns of the existing `users` table. These fields are used by the form-filling mapping to identify which data keys are available as source values. Fields marked `"source": "users"` are read directly from the `users` table; fields marked `"source": "user_details"` come from the `user_details.details` JSONB extension.

```json
{
  "parameter": "user_details",
  "setting": {
    "fields": [
      { "key": "first_name",       "label": "First Name",           "type": "text",  "required": true,  "source": "users" },
      { "key": "last_name",        "label": "Last Name",            "type": "text",  "required": true,  "source": "users" },
      { "key": "position",         "label": "Position",             "type": "text",  "required": false, "source": "users" },
      { "key": "phone_number",     "label": "Phone Number",         "type": "text",  "required": false, "source": "users" },
      { "key": "email",            "label": "Email",                "type": "email", "required": true,  "source": "users" },
      { "key": "company_name",     "label": "Company Name",         "type": "text",  "required": false, "source": "users" },
      { "key": "company_number",   "label": "Company Number",       "type": "text",  "required": false, "source": "users" },
      { "key": "company_address",  "label": "Company Address",      "type": "text",  "required": false, "source": "users" },
      { "key": "website",          "label": "Website",              "type": "text",  "required": false, "source": "users" },
      { "key": "notes",            "label": "Notes",                "type": "textarea", "required": false, "source": "user_details" }
    ]
  },
  "description": "Defines the data fields available for each user. Fields with source=users are read from the users table; fields with source=user_details come from the user_details.details JSONB extension. Used by form-filling mapping workflows."
}
```

### 3.2 Table: `user_details`

**Purpose:** Extended user data store for additional fields not in the `users` table. Each row links to the existing `users` table via `uuid`. The `details` JSONB column holds key-value pairs for any extra data fields defined in `system_config.user_details` (those with `"source": "user_details"`).

> **Note:** The existing `users` table (PK: `id uuid`) already contains core fields: `first_name`, `last_name`, `position`, `phone_number`, `email`, `company_name`, `company_number`, `company_address`, `website`. This extension table is for any additional fields beyond those.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `uuid` | PK, FK → `users.id` ON DELETE CASCADE | Links to existing users table |
| `details` | `jsonb` | NOT NULL, DEFAULT `'{}'::jsonb` | Key-value pairs for extended user data |
| `created_at` | `timestamptz` | DEFAULT now() | Record creation timestamp |
| `updated_at` | `timestamptz` | DEFAULT now() | Last modification timestamp |

**Behaviour:** When a new user is created, a trigger or workflow step should:
1. Read `system_config` where `parameter = 'user_details'`
2. Extract field keys where `source = 'user_details'`
3. Create a `user_details` row with those keys initialized to empty strings

**Example populated row:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "details": {
    "notes": "Technical lead for the Cambridge data centre project"
  }
}
```

### 3.3 Table: `pdf_ff_templates`

**Purpose:** Catalogue of PDF form templates available for automated filling. Each template is stored in the Supabase S3 bucket and its form fields are auto-discovered using the FF node's `Discover Fields` operation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `serial` | PK | Auto-increment ID |
| `template_ref` | `text` | UNIQUE, NOT NULL | Short reference code (e.g. `UKPN-G98`, `PP-APP-01`) |
| `title` | `text` | NOT NULL | Full title of the PDF form |
| `description` | `text` | | Purpose / when this form is used |
| `url_link` | `text` | NOT NULL | Path within Supabase bucket (e.g. `templates/UKPN-G98-Application.pdf`) |
| `source_site` | `text` | | URL where the blank template was originally obtained |
| `input_field_list` | `jsonb` | | Auto-discovered form fields (output of `Discover Fields`) |
| `source_to_template_mapping` | `jsonb` | | Mapping array: `[{ "pdfField": "...", "dataKey": "", "source": "" }]` |
| `version` | `text` | DEFAULT `'1.0'` | Template version |
| `date_added` | `timestamptz` | DEFAULT now() | When template was catalogued |
| `updated_at` | `timestamptz` | DEFAULT now() | Last modification timestamp |
| `status` | `text` | DEFAULT `'active'` | `active`, `deprecated`, `draft` |

**`input_field_list` structure** (from FF Discover Fields):
```json
{
  "fields": [
    { "name": "A1-First name", "type": "text", "required": false, "readOnly": false },
    { "name": "C-B", "type": "checkbox", "required": false, "readOnly": false }
  ],
  "fieldCount": 42
}
```

**`source_to_template_mapping` structure:**
```json
[
  {
    "pdfField": "A1-First name",
    "dataKey": "",
    "source": "users",
    "notes": ""
  },
  {
    "pdfField": "A1-Last name",
    "dataKey": "",
    "source": "users",
    "notes": ""
  },
  {
    "pdfField": "J-Start date",
    "dataKey": "",
    "source": "session_data",
    "dateFormat": "DD/MM/YYYY",
    "notes": ""
  }
]
```

The `source` field indicates where the data comes from:
- `users` — directly from the `users` table columns (first_name, last_name, email, etc.)
- `user_details` — from the `user_details.details` JSONB extension
- `session_data` — from the current workflow session/study context
- `manual` — must be provided at form-fill time
- `computed` — derived/calculated value

The `dataKey` field is initially empty (`""`) and must be manually mapped to match a key in the source data. This mapping is what the FF node's `Fill Form` operation uses as its `fieldMappings` input.

### 3.4 Table: `form_run_data`

**Purpose:** Audit trail for every form-filling execution. Records the inputs, outputs, and status of each fill operation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `serial` | PK | Auto-increment ID |
| `run_id` | `text` | NOT NULL | Workflow execution / session identifier |
| `template_id` | `integer` | FK → `pdf_ff_templates.id` | Which template was filled |
| `user_id` | `uuid` | FK → `users.id` | Which user's data was used |
| `form_values` | `jsonb` | | The resolved mapping with actual values used for filling |
| `fill_result` | `jsonb` | | FF node output: status, fieldsFilled, fieldsMissing, warnings |
| `final_pdf` | `text` | | Path to filled PDF in Supabase bucket |
| `status` | `text` | DEFAULT `'pending'` | `pending`, `filled`, `partial`, `error`, `submitted` |
| `created_at` | `timestamptz` | DEFAULT now() | Execution timestamp |
| `updated_at` | `timestamptz` | DEFAULT now() | Last status update |
| `notes` | `text` | | Any operator notes or error details |

**Example row after successful fill:**
```json
{
  "id": 1,
  "run_id": "Session-2026-02-15_14-30",
  "template_id": 3,
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "form_values": {
    "A1-First name": "Rainer",
    "A1-Last name": "Gaier",
    "A1-Company": "Ovations Group",
    "J-Start date": "15/02/2026"
  },
  "fill_result": {
    "status": "success",
    "fieldsFilled": 38,
    "fieldsMissing": 4,
    "fieldsSkipped": 0,
    "fieldsErrored": 0,
    "warnings": ["Mapped field 'site_mpan' has no value in data payload"]
  },
  "final_pdf": "form_runs/Session-2026-02-15_14-30/UKPN-G98-filled.pdf",
  "status": "filled"
}
```

---

## 4. Workflow Designs

### 4.1 Workflow: Add Form Template v0.1

**Purpose:** Upload a new PDF form template, catalogue it, and auto-discover its fields.

**Trigger:** Manual or Webhook (`POST /webhook/add-form-template`)

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | Unique execution identifier |
| `pdf_document` | binary | Yes | The blank PDF form template |
| `title` | string | Yes | Form title (e.g. "UKPN G98 Application") |
| `description` | string | Yes | Purpose of the form |
| `template_ref` | string | No | Short reference code (auto-generated if omitted) |
| `source_site` | string | No | URL where form was obtained |
| `version` | string | No | Template version (default: "1.0") |

**Node Flow:**
```
Trigger (Manual + Webhook)
  ↓
Extract Parameters
  ↓
Generate template_ref (if not provided)
  — slugify title, e.g. "ukpn-g98-application"
  ↓
Upload PDF to Supabase Bucket
  — path: templates/{template_ref}/{filename}
  — returns: url_link
  ↓
Discover Fields (FF Node)
  — input: PDF binary
  — output: FieldInfo[] + fieldCount
  ↓
Build Initial Mapping
  — For each discovered field:
    { "pdfField": field.name, "dataKey": "", "source": "", "notes": "" }
  ↓
Insert Record → pdf_ff_templates
  — template_ref, title, description, url_link
  — input_field_list: discover fields output
  — source_to_template_mapping: initial (empty) mapping array
  — source_site, version
  ↓
Return Summary
  — template_id, template_ref, fieldCount, url_link
  — message: "Template catalogued. Map fields in source_to_template_mapping."
```

### 4.2 Workflow: Fill Form v0.1

**Purpose:** Fill a PDF form using user data and the pre-configured mapping, then store the result.

**Design Decision:** This workflow should be a **separate, reusable sub-workflow** (not embedded in EnergyPlus v0.5). This allows any parent workflow to call it with a simple webhook/sub-workflow call. The parent workflow passes context; this workflow handles all form-filling mechanics.

**Trigger:** Webhook (`POST /webhook/fill-form`) or n8n Sub-Workflow call

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | Links to session/study |
| `template_ref` | string | Yes | Which template to fill (e.g. `UKPN-G98`) |
| `user_id` | uuid | Yes | Which user's data to use |
| `additional_data` | object | No | Extra key-value pairs beyond user data (e.g. session-specific data like dates, site references) |

**Node Flow:**
```
Trigger (Webhook / Sub-Workflow)
  ↓
Validate Inputs
  — Check template_ref exists in pdf_ff_templates
  — Check user_id exists in users
  ↓
Fetch Template Record
  — SELECT * FROM pdf_ff_templates WHERE template_ref = :ref
  — Extract: url_link, source_to_template_mapping
  ↓
Fetch User Data
  — SELECT u.*, ud.details FROM users u
    LEFT JOIN user_details ud ON ud.id = u.id
    WHERE u.id = :user_id
  — Flatten: merge users columns + user_details.details into single object
  ↓
Download PDF Template
  — GET from Supabase bucket: url_link
  — Returns: PDF binary
  ↓
Build Data Payload
  — Merge: flattened user data + additional_data
  — Result: flat JSON object with all available source data
  ↓
Build Field Mappings
  — Filter source_to_template_mapping to entries where dataKey != ""
  — Transform to FF node format: [{ "pdfField": "...", "dataKey": "..." }]
  ↓
Fill Form (FF Node — Dynamic Mode)
  — input: PDF binary + data payload + fieldMappings
  — output: filled PDF binary + FillFormResult
  ↓
Upload Filled PDF to Supabase Bucket
  — path: form_runs/{run_id}/{template_ref}-filled.pdf
  — returns: final_pdf path
  ↓
Insert Record → form_run_data
  — run_id, template_id, user_id
  — form_values: the resolved data payload
  — fill_result: FF node output (status, counts, warnings)
  — final_pdf: S3 path
  — status: derived from fill_result.status
  ↓
Return Result
  — run_id, status, final_pdf (full URL), fieldsFilled, fieldsMissing, warnings
```

### 4.3 Workflow: EnergyPlus v0.5

**Purpose:** Extend EnergyPlus v0.4 with a form-filling integration point. After simulation completes, if a form template is configured, trigger the Fill Form sub-workflow.

**Changes from v0.4:**
1. Add `user_id` and `form_templates` to input parameters
2. After `Final Summary` (or before), conditionally call `Fill Form v0.1` sub-workflow for each configured template
3. Include form-filling results in the final summary output

**New Input Parameters:**
```json
{
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "form_templates": ["PP-APP-01", "UKPN-G98"],
  "...existing v0.4 params..."
}
```

**Additional Flow (appended after simulation export):**
```
...existing v0.4 flow...
  ↓
Check Form Templates
  — IF form_templates is not empty AND user_id is set
  ↓
For Each Template
  — Call Fill Form v0.1 sub-workflow
  — Pass: run_id (session_id), template_ref, user_id
  — Pass: additional_data from simulation context (project_name, location, dates)
  ↓
Collect Form Results
  — Aggregate results from all form fills
  ↓
Enhanced Final Summary
  — Include form_results array in output
```

---

## 5. Supabase Bucket Structure

Extend the existing `panicleDevelop_1` bucket:

```
panicleDevelop_1/
├── {session_id}/                    # Existing simulation outputs
│   └── {analysis_type}/
│       └── ... (simulation files)
├── templates/                       # NEW — PDF form templates
│   ├── ukpn-g98/
│   │   └── UKPN-G98-Application.pdf
│   ├── pp-app-01/
│   │   └── Planning-Permission-Application.pdf
│   └── .../
└── form_runs/                       # NEW — Filled PDF outputs
    ├── Session-2026-02-15_14-30/
    │   ├── ukpn-g98-filled.pdf
    │   └── pp-app-01-filled.pdf
    └── .../
```

---

## 6. Future Enhancement: Automated Field Mapping

**Problem:** The `source_to_template_mapping` must currently be manually populated — linking each PDF field name (e.g. `"A1-First name"`) to a data key (e.g. `"first_name"`). For forms with 40+ fields, this is tedious.

**Proposed Approach — Similarity-Based Auto-Mapping:**

1. **Normalise field names:** Strip prefixes (e.g. `A1-`), convert to lowercase, replace hyphens/underscores with spaces
2. **Compare against user data field labels:** Use string similarity (Levenshtein distance or cosine similarity on character n-grams)
3. **Threshold match:** If similarity > 0.7, auto-suggest the mapping
4. **Human review:** Present suggested mappings for confirmation, flag uncertain ones

**Example:**
| PDF Field | Normalised | Best Match (user data) | Score | Auto-Map? |
|-----------|-----------|-------------------------|-------|-----------|
| `A1-First name` | `first name` | `first_name` (label: "First Name") | 0.95 | Yes |
| `A1-Postcode` | `postcode` | `postcode` (label: "Postcode") | 1.00 | Yes |
| `J-Start date` | `start date` | — | 0.00 | No (session_data) |
| `C-B` | `c b` | — | 0.00 | No (manual) |

This could be implemented as:
- A JavaScript Code node in the Add Template workflow (lightweight, no extra deps)
- Or an n8n AI node using an LLM to interpret field semantics (more accurate, higher cost)

**Recommendation:** Start with the normalisation + similarity approach in a Code node. It handles the 60-70% of fields that have obvious names. Leave the rest for manual mapping. Upgrade to LLM-based mapping later if the manual burden is too high.

---

## 7. Implementation Plan

### Phase 1: Database Foundation ~~(Rob)~~ — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1.1 | Review database schema (`CR-001-database-schema.sql`) | Rob | Done | Authorised Rainer to create |
| 1.2 | Create tables in Supabase | Rainer | Done | 4 tables created 2026-02-16 |
| 1.3 | Confirm existing `users` table structure | Rob | Done | PK: `id uuid`, schema confirmed |
| 1.4 | Seed `system_config` with `user_details` parameter | Rainer | Pending | INSERT from SQL file |
| 1.5 | Set up Supabase bucket folders (`templates/`, `form_runs/`) | Rainer | Pending | Auto-created on first upload |
| 1.6 | RLS decision | Rainer/Rob | Done | Deferred — service_role key bypasses RLS |

### Phase 2: Template Management Workflow (Rainer) — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 2.1 | Create `Add Form Template v0.1` workflow in n8n | Rainer | Done | `n8n/Add_Form-Template v0.2.json` |
| 2.2 | Test with UKPN G98 form (from FF project test fixtures) | Rainer | Done | Template catalogued, fields discovered |
| 2.3 | Manually populate `source_to_template_mapping` for UKPN G98 | Rainer | Done | Complete mapping |
| 2.4 | Test with a second form (planning permission or similar) | Rainer | Done | TST-001 tested |
| 2.5 | Evolve to v0.3 with fuzzy auto-mapping (Levenshtein + Jaccard) | Rainer | Done | `n8n/Add Form Template v0.3.json` |
| 2.6 | Evolve to v0.4 with Excel export + Supabase upload | Rainer | Done | `n8n/Add Form Template v0.4.json` |

### Phase 3: Form Filling Workflow (Rainer) — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 3.1 | Create `Fill Form v0.1` sub-workflow | Rainer | Done | `n8n/Fill_Form v0.1.json` |
| 3.2 | Test standalone with UKPN G98 + test user | Rainer | Done | Filled PDF in bucket |
| 3.3 | Verify `form_run_data` audit record | Rainer | Done | Record with status, values, PDF link |
| 3.4 | Create `Form Fill Demo v0.1` end-to-end demo workflow | Rainer | Done | `n8n/Form Fill Demo v0.1.json` |

### Phase 4: EnergyPlus Integration (Rainer) — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 4.1 | Create `EnergyPlus v0.5.json` extending v0.4 | Rainer | Done | Workflow with form-filling step |
| 4.2 | End-to-end test: simulation → form fill → export | Rainer | Done | Complete run with all outputs |
| 4.3 | Update roadmap and documentation | Rainer | Done | Updated `ROADMAP.md` |

### Phase 5: Auto-Mapping Enhancement (Rainer) — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 5.1 | Implement similarity-based auto-mapping in Add Template workflow | Rainer | Done | Levenshtein + Jaccard in v0.3 Code node |
| 5.2 | Test accuracy across multiple form templates | Rainer | Done | Good accuracy on UKPN G98, TST-001 |

### Phase 6: Mapping Management (Rainer) — COMPLETE

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 6.1 | Add Excel export of mapping to Add Form Template v0.4 | Rainer | Done | 7-column xlsx with override column |
| 6.2 | Upload mapping Excel to Supabase alongside PDF template | Rainer | Done | `PDF-templates/{ref}/{ref}_mapping.xlsx` |
| 6.3 | Create `Allocate Form Mapping v0.1` workflow | Rainer | Done | Download Excel → parse overrides → validate → update Supabase |
| 6.4 | Graceful error handling for missing mapping file | Rainer | Done | Returns status JSON instead of throwing |

---

## 8. Open Questions

| # | Question | For | Status |
|---|----------|-----|--------|
| Q1 | ~~Does a `stakeholders` table already exist in Supabase?~~ **Resolved:** Existing table is `users` (PK: `id uuid`). Schema confirmed. | Rob | Closed |
| Q2 | Should `system_config` support versioning (multiple versions of same parameter)? | Rob/Rainer | Open |
| Q3 | Should filled PDFs be downloadable via a public URL or require authentication? | Rob | Open |
| Q4 | Is there a preference for the `template_ref` naming convention? | Rob/Rainer | Open |
| Q5 | Are there specific PDF forms Rob wants to prioritise for the first test? | Rob | Open |
| Q6 | Does the sub-workflow approach work for Rob's orchestration model, or should form-filling be inline? | Rob | Open |

---

## 9. File Inventory

Files created/modified by this CR:

| File | Project | Type | Description |
|------|---------|------|-------------|
| `roadmap/planning/CR-001-form-handling-integration.md` | EP | New | This change request (you're reading it) |
| `roadmap/planning/CR-001-database-schema.sql` | EP | New | SQL schema for Rob to review |
| `roadmap/planning/CR-002-user-details-extension.md` | EP | New | User details extension (mobile, postcode, title) |
| `roadmap/planning/CR-002-user-details-extension.sql` | EP | New | SQL for CR-002 |
| `n8n/Add_Form-Template v0.2.json` | EP | New | Template cataloguing workflow (initial) |
| `n8n/Add Form Template v0.4.json` | EP | New | Template cataloguing with fuzzy mapping + Excel export |
| `n8n/Fill_Form v0.1.json` | EP | New | Form filling sub-workflow |
| `n8n/Form Fill Demo v0.1.json` | EP | New | End-to-end form fill demo workflow |
| `n8n/Allocate Form Mapping v0.1.json` | EP | New | Excel-based mapping management workflow |
| `n8n/EnergyPlus v0.5.json` | EP | New | Extended simulation workflow with form-filling |

---

## 10. Appendix: FF Node Interface Reference

### Discover Fields Operation
- **Input:** PDF binary (property: `data`)
- **Output JSON:** `{ fields: FieldInfo[], fieldCount: number }`
- **FieldInfo:** `{ name, type, required, currentValue, options, readOnly }`

### Fill Form Operation (Dynamic Mode)
- **Input:** PDF binary + JSON data + `fieldMappings` property
- **fieldMappings format:** `[{ dataKey: string, pdfField: string, dateFormat?: string }]`
- **Output JSON:** `{ status, fieldsFilled, fieldsMissing, fieldsSkipped, fieldsErrored, warnings, fileName }`
- **Output Binary:** Filled PDF

### Supported Field Types
`text`, `checkbox`, `radio`, `dropdown`, `optionList`, `signature`, `button`, `unknown`

### Key Behaviours
- Field names are **case-sensitive** and **whitespace-sensitive**
- `dataKey` supports **dot-notation** for nested objects (e.g. `address.postcode`)
- Missing data values generate **warnings** (not errors) — the fill continues
- `form.updateFieldAppearances()` is called automatically to make filled values visible
