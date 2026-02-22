-- =============================================================================
-- CR-002: User Details Extension — Mobile, Postcode & Title
-- =============================================================================
-- Project:  EnergyPlus MCP Server
-- Author:   Rainer Gaier / Claude
-- Date:     2026-02-17
-- Depends:  CR-001 (tables: system_config, user_details, users)
-- Status:   APPLIED — 2026-02-17
--
-- This script:
--   1. Updates system_config to add mobile_number, postcode, title fields
--   2. Creates upsert_user_details() stored procedure
--   3. Seeds sample data for test user f24ee278-fb1e-42dc-8777-ac9af1954d25
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 1. Update system_config — Add new user_details fields
-- ---------------------------------------------------------------------------
-- Replaces the existing 'user_details' setting with an expanded field list.
-- New fields: mobile_number, postcode, title (all source = 'user_details')

UPDATE system_config
SET setting = '{
    "fields": [
        { "key": "first_name",       "label": "First Name",       "type": "text",     "required": true,  "source": "users" },
        { "key": "last_name",        "label": "Last Name",        "type": "text",     "required": true,  "source": "users" },
        { "key": "position",         "label": "Position",         "type": "text",     "required": false, "source": "users" },
        { "key": "phone_number",     "label": "Phone Number",     "type": "text",     "required": false, "source": "users" },
        { "key": "email",            "label": "Email",            "type": "email",    "required": true,  "source": "users" },
        { "key": "company_name",     "label": "Company Name",     "type": "text",     "required": false, "source": "users" },
        { "key": "company_number",   "label": "Company Number",   "type": "text",     "required": false, "source": "users" },
        { "key": "company_address",  "label": "Company Address",  "type": "text",     "required": false, "source": "users" },
        { "key": "website",          "label": "Website",          "type": "text",     "required": false, "source": "users" },
        { "key": "mobile_number",    "label": "Mobile Number",    "type": "text",     "required": false, "source": "user_details" },
        { "key": "postcode",         "label": "Postcode",         "type": "text",     "required": false, "source": "user_details" },
        { "key": "title",            "label": "Title",            "type": "text",     "required": false, "source": "user_details", "hint": "e.g. Mr, Mrs, Ms, Dr" },
        { "key": "notes",            "label": "Notes",            "type": "textarea", "required": false, "source": "user_details" }
    ]
}'::jsonb,
    description = 'Defines the data fields available for each user. Fields with source=users are read from the users table; fields with source=user_details come from the user_details.details JSONB extension. Updated CR-002: added mobile_number, postcode, title.'
WHERE parameter = 'user_details';


-- ---------------------------------------------------------------------------
-- 2. Stored procedure: upsert_user_details
-- ---------------------------------------------------------------------------
-- Merges provided JSONB keys into user_details.details for a given user.
-- Creates the user_details row if it doesn't exist (handles pre-trigger users).
--
-- Usage:
--   SELECT upsert_user_details(
--     'f24ee278-fb1e-42dc-8777-ac9af1954d25',
--     '{"mobile_number": "07700 900123", "postcode": "CB1 2AB", "title": "Mr"}'
--   );
--
-- Merge behaviour:
--   - Only overwrites keys present in p_details
--   - Preserves existing keys not mentioned in p_details
--   - To clear a key, pass it as empty string: '{"notes": ""}'

CREATE OR REPLACE FUNCTION upsert_user_details(
    p_user_id uuid,
    p_details jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_result jsonb;
BEGIN
    -- Insert or update, merging JSONB with || operator
    INSERT INTO user_details (id, details, updated_at)
    VALUES (p_user_id, p_details, now())
    ON CONFLICT (id) DO UPDATE
    SET
        details = user_details.details || p_details,
        updated_at = now()
    RETURNING details INTO v_result;

    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION upsert_user_details(uuid, jsonb)
IS 'Merges provided JSONB keys into user_details.details. Creates row if missing. Returns updated details.';


-- ---------------------------------------------------------------------------
-- 3. Seed data — Test user
-- ---------------------------------------------------------------------------
-- Populates user_details for the test user used in workflow testing.
-- Uses the new stored procedure to demonstrate its usage.

SELECT upsert_user_details(
    'f24ee278-fb1e-42dc-8777-ac9af1954d25'::uuid,
    '{
        "mobile_number": "07700 900456",
        "postcode": "CB2 1TN",
        "title": "Mr",
        "notes": "Rob extended test data for form-filling demo"
    }'::jsonb
);

SELECT upsert_user_details(
    '4a62ed11-6360-41fe-81fb-72f711f23f4b'::uuid,
    '{
        "mobile_number": "+27832883402",
        "postcode": "CB22195",
        "title": "Mr",
        "notes": "Rainer extended test data for form-filling demo"
    }'::jsonb
);


-- ---------------------------------------------------------------------------
-- Verification queries (run after applying)
-- ---------------------------------------------------------------------------

-- Check system_config has the new fields
-- SELECT setting->'fields' FROM system_config WHERE parameter = 'user_details';

-- Check user_details was populated
-- SELECT id, details FROM user_details WHERE id = 'f24ee278-fb1e-42dc-8777-ac9af1954d25';

-- List all user_details source fields
-- SELECT f->>'key' AS field_key, f->>'label' AS label, f->>'source' AS source
-- FROM system_config, jsonb_array_elements(setting->'fields') AS f
-- WHERE parameter = 'user_details' AND f->>'source' = 'user_details';


-- =============================================================================
-- END OF CR-002
-- =============================================================================
