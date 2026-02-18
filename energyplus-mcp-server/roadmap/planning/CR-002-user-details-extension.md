# CR-002: User Details Extension — Mobile, Postcode & Title

**Status:** Implemented — 2026-02-17
**Author:** Rainer Gaier / Claude
**Date:** 2026-02-17
**Depends on:** CR-001 (Form Handling & User Data Integration)
**Reviewer(s):** Rob (database), Rainer (workflows)

---

## 1. Context & Motivation

CR-001 introduced the `user_details` extension table with a JSONB `details` column and a `system_config` seed defining available fields. Currently only `notes` is defined as a `user_details` source field — all other user data comes from the `users` table columns.

The fuzzy auto-mapping algorithm (Add Form Template v0.3) maps PDF fields like "Mobile", "Postcode", and "Title/Salutation" to data keys `mobile_number`, `postcode`, and `title`. These fields don't exist on the `users` table, so they need to live in `user_details.details`.

Without this change, any form fields mapped to these keys will produce empty values during Fill Form execution.

---

## 2. Scope

### 2.1 Changes Required

1. **Update `system_config` seed** — Add `mobile_number`, `postcode`, `title` to the `user_details` field definitions with `source: 'user_details'`
2. **Populate `user_details.details`** — Seed existing users' JSONB with the new keys
3. **Stored procedure** — Create `upsert_user_details(p_user_id, p_details)` to simplify future updates from n8n workflows or API calls

### 2.2 Out of Scope

- Changes to the `users` table schema
- UI for editing user_details (future CR)
- RLS policies (deferred per CR-001)

---

## 3. Implementation

### 3.1 Update system_config field definitions

Add the three new fields to the existing `user_details` parameter in `system_config`. This is an UPDATE (not INSERT) since the row already exists.

### 3.2 Stored procedure: `upsert_user_details`

**Rationale:** Currently, updating `user_details.details` requires constructing a JSONB merge manually in every workflow or API call. A stored procedure provides:
- A single, consistent entry point for updates
- JSONB merge semantics (only overwrites provided keys, preserves others)
- Automatic `updated_at` timestamping
- Auto-creation of the `user_details` row if it doesn't exist (handles users created before the trigger was installed)

The procedure accepts a user UUID and a JSONB object, then merges the provided keys into the existing `details` column using the `||` operator.

### 3.3 Seed data

Populate test user(s) with sample values for demo purposes.

---

## 4. Risk & Rollback

- **Low risk** — additive changes only, no schema modifications to existing tables
- **Rollback** — DELETE the new fields from `system_config.setting` and SET `details = '{}'` on affected `user_details` rows
- **No downtime** — all changes are backwards-compatible

---

## 5. Testing

- Run Fill Form workflow with a template that has fields mapped to `mobile_number`, `postcode`, `title`
- Verify the filled PDF contains the correct values
- Test `upsert_user_details` with partial updates (only some keys) to confirm merge behaviour
