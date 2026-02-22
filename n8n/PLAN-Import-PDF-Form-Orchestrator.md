# Plan: Import PDF Form v0.1 (Grandioso) — Orchestrator Workflow

## Overview

A master n8n workflow that orchestrates the entire PDF form processing pipeline:
upload a blank PDF → discover fields → map them → fill data gaps → fill the form.

It calls the 7 existing sub-workflows in sequence, pausing with an HTML form
when human intervention is needed (Excel editing), and tracking progress in
Supabase so runs can be resumed from any step.

---

## Design Decisions (confirmed with user)

| Decision | Choice |
|----------|--------|
| LLM step (step 5) | Run straight through, no pause |
| Human wait method | n8n Wait node in "Form" mode — renders HTML with instructions + Resume button |
| PDF upload | User uploads PDF to Supabase before starting; passes storage path to orchestrator |

---

## Pipeline Steps

| Step | Name | Sub-Workflow | Human Pause? | Path |
|------|------|-------------|-------------|------|
| 1 | Add Form Template | Add Form Template v0.5 | YES — edit Mapping + Extended Info Excel | Both |
| 2 | Allocate Form Mapping | Allocate Form Mapping v0.1 | No | Both |
| 3 | Path decision | (Code node) | No — auto or user-chosen at step 1 form | Both |
| 3a | Update Extended Data | Update Extended Data v0.1 | No | Path A only |
| 3b | Analyse Form Gaps | Analyse Form Gaps v0.1 | YES — edit gap report → Generate_Data.xlsx | Path B only |
| 4 | Generate Synthetic Data | Generate Synthetic Data v0.1 | No | Path B only |
| 5 | Generate Realistic Data | Generate Realistic Data v0.1 | No (auto-applies) | Path B only |
| 6 | Fill Form | Fill Form v0.1 | No | Both |

Path A = simple (all fields auto-mapped or manually mapped via Excel)
Path B = full (gap analysis → synthetic → realistic → fill)

---

## State Tracking: `pipeline_runs` table

```sql
CREATE TABLE pipeline_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id text UNIQUE NOT NULL,
  template_ref text NOT NULL,
  user_id uuid NOT NULL,
  current_step integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'pending',  -- pending, running, paused, completed, failed, aborted
  path text NOT NULL DEFAULT 'undecided',  -- undecided, path_a, path_b
  steps_completed jsonb NOT NULL DEFAULT '[]'::jsonb,
  step_results jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_error text,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  completed_at timestamptz
);
```

Key design: each step checks `steps_completed` before executing → idempotent,
so re-running from step N skips already-completed steps.

---

## Node-by-Node Flow

### Entry (nodes 1-4)

```
[Manual Trigger]
  → [Default Params] (Code) — set run_id, template_ref, user_id, pdf_path,
     start_from_step (default 1), config (domain_context, min_score, openai_api_key)
  → [Init Pipeline State] (HTTP POST to Supabase) — INSERT into pipeline_runs
     (or UPDATE if run_id already exists, to support resume)
  → [Route to Step] (Switch on current_step)
```

### Step 1: Add Form Template

```
[Check Step 1 Done] (Code — skip if 1 in steps_completed)
  → [Call Add Form Template] (HTTP POST /webhook/add-form-template)
     Body: { run_id, title, description, template_ref, pdf_storage_path }
  → [Check Step 1 Result] (Code — error handling)
  → [Mark Step 1 Complete] (HTTP PATCH pipeline_runs)
  → [Wait: Review Mapping Files] (Wait node, mode: "On form submission")
     HTML form shows:
       - Summary: X fields discovered, Y auto-mapped, Z need review
       - Instructions:
         1. Download {ref}_mapping.xlsx from Supabase storage
         2. Edit column F "Manual Override" for any corrections
         3. Download {ref}_extended_info.xlsx
         4. Fill columns D-E for new data fields needed
         5. Upload both edited files back to Supabase storage
       - Path choice: radio buttons (Path A / Path B)
       - Buttons: [Resume] [Abort]
  → [Process Step 1 Resume] (Code — extract path choice, handle abort)
  → [Update State: step=2, path=chosen] (HTTP PATCH)
  → [Route to Step 2]
```

### Step 2: Allocate Form Mapping

```
[Check Step 2 Done]
  → [Call Allocate Form Mapping] (HTTP POST /webhook/allocate-form-mapping)
     Body: { template_ref }
  → [Check Step 2 Result]
  → [Mark Step 2 Complete]
  → [Route by Path] (If node: path == 'path_a' → step 3a, else → step 3b)
```

### Step 3a: Update Extended Data (Path A)

```
[Check Step 3a Done]
  → [Call Update Extended Data] (HTTP — needs webhook adding to sub-workflow,
     OR use Execute Workflow node)
     Body: { template_ref, user_id }
  → [Check Step 3a Result]
  → [Mark Step 3a Complete]
  → [Update State: step=6] (skip to Fill Form)
  → [Route to Step 6]
```

### Step 3b: Analyse Form Gaps (Path B)

```
[Check Step 3b Done]
  → [Call Analyse Form Gaps] (HTTP — needs webhook adding, OR Execute Workflow)
     Body: { template_ref, min_score }
  → [Check Step 3b Result]
  → [Mark Step 3b Complete]
  → [Wait: Review Gap Report] (Wait node, mode: "On form submission")
     HTML form shows:
       - Summary: X unmapped fields found, Y suggestions above threshold
       - Instructions:
         1. Download gap report from Supabase
         2. Add "Create Data" column — TRUE for fields to auto-generate
         3. Save as Generate_Data.xlsx
         4. Upload to Supabase: PDF-templates/{template_ref}/Generate_Data.xlsx
       - Buttons: [Resume] [Abort]
  → [Process Step 3b Resume]
  → [Update State: step=4]
  → [Route to Step 4]
```

### Step 4: Generate Synthetic Data (Path B)

```
[Check Step 4 Done]
  → [Call Generate Synthetic Data] (HTTP — needs webhook, OR Execute Workflow)
     Body: { template_ref, user_id }
  → [Check Step 4 Result]
  → [Mark Step 4 Complete]
  → [Update State: step=5]
  → [Route to Step 5]
```

### Step 5: Generate Realistic Data (Path B) — runs straight through

```
[Check Step 5 Done]
  → [Call Generate Realistic Data] (HTTP POST /webhook/generate-realistic-data)
     Body: { template_ref, user_id, openai_api_key, domain_context }
  → [Check Step 5 Result]
  → [Mark Step 5 Complete]
  → [Update State: step=6]
  → [Route to Step 6]
```

### Step 6: Fill Form (both paths converge)

```
[Check Step 6 Done]
  → [Call Fill Form] (HTTP POST /webhook/fill-form)
     Body: { run_id, template_ref, user_id, additional_data: {} }
  → [Check Step 6 Result]
  → [Mark Step 6 Complete]
  → [Update State: status=completed, completed_at=now()]
  → [Return Final Summary]
     - Pipeline status
     - Steps completed with results
     - Filled PDF URL
     - Duration
     - Warnings/errors
```

---

## Resume-from-Step Mechanism

The orchestrator supports starting from any step via `start_from_step` parameter:

1. On trigger, if `start_from_step > 1`:
   - UPSERT into `pipeline_runs` (create or update existing record)
   - Set `current_step = start_from_step`
   - Route directly to that step via the Switch node
2. Each step's "Check Done" code node: if step number is in `steps_completed` array → skip
3. This means re-running from step 4 will skip steps 1-3 automatically

For **Wait node resume** (after Excel editing):
- The Wait node generates a unique URL
- When the user submits the form, n8n resumes the paused execution
- No separate webhook needed — n8n handles this natively

---

## Sub-Workflow Webhook Gaps

Some sub-workflows currently only have Manual triggers (no webhook). We need to
add webhook triggers to these before the orchestrator can call them:

| Sub-Workflow | Has Webhook? | Action Needed |
|-------------|-------------|---------------|
| Add Form Template v0.5 | YES | None |
| Allocate Form Mapping v0.1 | YES | None |
| Update Extended Data v0.1 | NO (manual only) | Add webhook trigger |
| Analyse Form Gaps v0.1 | NO (manual only) | Add webhook trigger |
| Generate Synthetic Data v0.1 | NO (manual only) | Add webhook trigger |
| Generate Realistic Data v0.1 | YES | None |
| Fill Form v0.1 | YES | None |

**3 sub-workflows need webhook triggers added** before the orchestrator can call them.

---

## Error Handling

Each sub-workflow call follows this pattern:

```
[Call Sub-Workflow] (HTTP Request, onError: continueRegularOutput)
  → [Check Result] (Code node)
     - If HTTP status >= 400 OR response.status == 'error':
       → Update pipeline_runs: status='failed', last_error=message
       → Return error with: step name, error message, suggestion
     - If success:
       → Continue to next step
```

On failure, the user can:
1. Fix the issue
2. Re-run orchestrator with same `run_id` and `start_from_step` = failed step
3. Completed steps are skipped automatically

---

## Implementation Steps

### Phase 1: Database Setup
1. Create `pipeline_runs` table in Supabase

### Phase 2: Add Missing Webhook Triggers
2. Add webhook trigger to Update Extended Data v0.1
3. Add webhook trigger to Analyse Form Gaps v0.1
4. Add webhook trigger to Generate Synthetic Data v0.1

### Phase 3: Build Orchestrator Workflow
5. Create `Import PDF Form v0.1.json` with all nodes:
   - Entry: Manual Trigger → Default Params → Init State → Route
   - Step 1: Call + Wait Form + Resume
   - Step 2: Call + Route by path
   - Step 3a: Call (Path A)
   - Step 3b: Call + Wait Form + Resume (Path B)
   - Steps 4-5: Call (Path B, straight through)
   - Step 6: Call Fill Form + Final Summary
6. Add error handling to each step

### Phase 4: Testing
7. Test resume-from-step with start_from_step parameter
8. Test full Path A pipeline
9. Test full Path B pipeline

---

## Input Parameters (Manual Trigger Default Params)

```json
{
  "run_id": "Import-APP001-2026-02-22",
  "template_ref": "APP-001",
  "user_id": "f24ee278-fb1e-42dc-8777-ac9af1954d25",
  "title": "UK Planning Application (1APP)",
  "description": "Standard planning application form for England",
  "pdf_storage_path": "PDF-templates/APP-001/G2625Form004_england_en.pdf",
  "start_from_step": 1,
  "config": {
    "min_score": 0.70,
    "domain_context": "UK planning application form submission",
    "openai_api_key": "{{ $env.OPENAI_API_KEY }}"
  }
}
```

---

## Estimated Node Count

~50 nodes (uses If-chain routing instead of Switch node).

---

## Planned Enhancements

### ENH-001: Sync new data keys back to `system_config` (IMPLEMENTED)

**Problem:** When Steps 4-5 (Generate Synthetic/Realistic Data) create new data keys
in `user_details` (e.g., `site_address`, `planning_reference_number`), those keys are
NOT added back to `system_config.setting.fields[]`.

**Fix (applied):** Added automated sync between Steps 4 and 5 in the orchestrator:

1. After Step 4 (Generate Synthetic), fetches `system_config` and `user_details` in parallel
2. "Build Config Sync" Code node diffs registered keys vs actual `user_details.details` keys
3. "Sync Needed?" If node checks if new keys were found
4. If yes: "Update System Config" PATCHes `system_config.setting.fields[]` with new entries
   (auto-generates label from key, sets type=text, required=false, source=user_details)
5. Both paths converge at Step 5 (Call: Generate Realistic)

**Also available:** Ad-hoc SQL script `CR-003-sync-system-config.sql` for manual runs.

**Status:** Implemented in Import PDF Form v0.1.json (5 new nodes, 55 total).

### ENH-002: Dynamic fuzzy matching from `system_config` (IMPLEMENTED)

**Problem:** The "Build Initial Mapping" Code node in Add Form Template v0.5 had a
hardcoded array of only 12 data keys with hand-crafted aliases. It could only ever
match PDF fields against those 12 keys, ignoring all keys created by Generate Synthetic
Data or manual Extended Info edits. This meant re-running Step 1 for a new template
after processing a previous one gained no benefit from accumulated data.

**Fix (applied):** Replaced the hardcoded `userFields` array with a dynamic approach:

1. Added a new "Fetch System Config" HTTP Request node that queries
   `GET /rest/v1/system_config?parameter=eq.user_details&limit=1` at runtime
2. Rewired: `If (has fields?) → Fetch System Config → Build Initial Mapping`
3. Rewrote Build Initial Mapping to:
   - Load all fields from `system_config.setting.fields[]`
   - Preserve hand-crafted aliases for the original 12 core keys (high-quality matches)
   - Auto-generate aliases for all other keys: `key.replace(/_/g, ' ')` + raw key +
     individual significant words (5+ chars)
   - Merge both into a single `userFields` array for the fuzzy matcher

**Dependency:** Requires CR-003 (sync system_config) to have been run at least once
after previous pipeline runs, so that new data keys are registered.

**Status:** Implemented in Add Form Template v0.5.json.
