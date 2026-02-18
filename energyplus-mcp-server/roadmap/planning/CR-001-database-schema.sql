-- =============================================================================
-- CR-001: Form Handling & User Data Integration — Database Schema
-- =============================================================================
-- Project:  EnergyPlus MCP Server (Stakeholder-Informed Agentic System)
-- Author:   Rainer Gaier
-- Date:     2026-02-16 (rev 2)
-- Status:   APPLIED — Tables created 2026-02-16
-- Supabase: egrzvwnjrtpwwmqzimff.supabase.co
--
-- NOTES FOR ROB:
-- 1. This references the existing 'users' table (PK: id uuid).
--    Confirmed columns: id, first_name, last_name, position, phone_number,
--    email, company_name, company_number, company_address, website,
--    created_at, updated_at.
-- 2. All JSONB columns use Supabase-friendly types.
-- 3. The trigger function auto-populates user_details when a new
--    user is created — adjust if your insert workflow differs.
-- 4. RLS deferred — service_role key bypasses RLS. Enable when a
--    frontend app exposes these tables to end users via anon/JWT.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 1. system_config — Global key-value configuration store
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS system_config (
    id          serial       PRIMARY KEY,
    parameter   text         NOT NULL UNIQUE,
    setting     jsonb        NOT NULL DEFAULT '{}'::jsonb,
    description text,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  system_config IS 'Global system configuration parameters (key-value store)';
COMMENT ON COLUMN system_config.parameter IS 'Unique config key, e.g. user_details';
COMMENT ON COLUMN system_config.setting IS 'JSONB config value — structure varies by parameter';

-- Auto-update updated_at (shared by all tables in this schema)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Seed: user_details field definitions
-- Fields with source=users are read directly from the users table.
-- Fields with source=user_details come from user_details.details JSONB.
INSERT INTO system_config (parameter, setting, description)
VALUES (
    'user_details',
    '{
        "fields": [
            { "key": "first_name",       "label": "First Name",       "type": "text",  "required": true,  "source": "users" },
            { "key": "last_name",        "label": "Last Name",        "type": "text",  "required": true,  "source": "users" },
            { "key": "position",         "label": "Position",         "type": "text",  "required": false, "source": "users" },
            { "key": "phone_number",     "label": "Phone Number",     "type": "text",  "required": false, "source": "users" },
            { "key": "email",            "label": "Email",            "type": "email", "required": true,  "source": "users" },
            { "key": "company_name",     "label": "Company Name",     "type": "text",  "required": false, "source": "users" },
            { "key": "company_number",   "label": "Company Number",   "type": "text",  "required": false, "source": "users" },
            { "key": "company_address",  "label": "Company Address",  "type": "text",  "required": false, "source": "users" },
            { "key": "website",          "label": "Website",          "type": "text",  "required": false, "source": "users" },
            { "key": "notes",            "label": "Notes",            "type": "textarea", "required": false, "source": "user_details" }
        ]
    }'::jsonb,
    'Defines the data fields available for each user. Fields with source=users are read from the users table; fields with source=user_details come from the user_details.details JSONB extension. Used by form-filling mapping workflows.'
)
ON CONFLICT (parameter) DO NOTHING;


-- ---------------------------------------------------------------------------
-- 2. user_details — Extended user data (links to users via uuid)
-- ---------------------------------------------------------------------------
-- The existing users table already has core fields (first_name, last_name,
-- email, etc.). This extension table holds any additional key-value data
-- defined in system_config where source = 'user_details'.

CREATE TABLE IF NOT EXISTS user_details (
    id          uuid         PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    details     jsonb        NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  user_details IS 'Extended key-value data for each user, driven by system_config.user_details';
COMMENT ON COLUMN user_details.details IS 'JSONB object with keys for fields where source=user_details in system_config';

CREATE TRIGGER trg_user_details_updated_at
    BEFORE UPDATE ON user_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: auto-create user_details row when a new user is inserted
-- Reads field keys (where source=user_details) from system_config
-- and creates an empty JSONB object with those keys
CREATE OR REPLACE FUNCTION auto_create_user_details()
RETURNS TRIGGER AS $$
DECLARE
    field_keys jsonb;
    empty_details jsonb := '{}'::jsonb;
    field_record jsonb;
BEGIN
    -- Get field definitions from system_config
    SELECT setting->'fields' INTO field_keys
    FROM system_config
    WHERE parameter = 'user_details';

    -- Build empty details object from fields where source = 'user_details'
    IF field_keys IS NOT NULL THEN
        FOR field_record IN SELECT * FROM jsonb_array_elements(field_keys)
        LOOP
            -- Only include fields that belong in the user_details extension table
            IF field_record->>'source' = 'user_details' THEN
                empty_details := empty_details || jsonb_build_object(
                    field_record->>'key',
                    COALESCE(field_record->>'default', '')
                );
            END IF;
        END LOOP;
    END IF;

    INSERT INTO user_details (id, details)
    VALUES (NEW.id, empty_details)
    ON CONFLICT (id) DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_create_user_details
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_user_details();


-- ---------------------------------------------------------------------------
-- 3. pdf_ff_templates — PDF form template catalogue
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pdf_ff_templates (
    id                          serial       PRIMARY KEY,
    template_ref                text         NOT NULL UNIQUE,
    title                       text         NOT NULL,
    description                 text,
    url_link                    text         NOT NULL,
    source_site                 text,
    input_field_list            jsonb,
    source_to_template_mapping  jsonb,
    version                     text         DEFAULT '1.0',
    date_added                  timestamptz  NOT NULL DEFAULT now(),
    updated_at                  timestamptz  NOT NULL DEFAULT now(),
    status                      text         NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'deprecated', 'draft'))
);

COMMENT ON TABLE  pdf_ff_templates IS 'Catalogue of PDF form templates available for automated filling';
COMMENT ON COLUMN pdf_ff_templates.template_ref IS 'Short reference code, e.g. UKPN-G98, PP-APP-01';
COMMENT ON COLUMN pdf_ff_templates.url_link IS 'Path within Supabase bucket (e.g. templates/ukpn-g98/form.pdf)';
COMMENT ON COLUMN pdf_ff_templates.input_field_list IS 'Auto-discovered form fields from Discover Fields operation';
COMMENT ON COLUMN pdf_ff_templates.source_to_template_mapping IS 'Array of {pdfField, dataKey, source, notes} mapping entries';

CREATE TRIGGER trg_pdf_ff_templates_updated_at
    BEFORE UPDATE ON pdf_ff_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Index for lookups by template_ref
CREATE INDEX IF NOT EXISTS idx_pdf_ff_templates_ref ON pdf_ff_templates (template_ref);
CREATE INDEX IF NOT EXISTS idx_pdf_ff_templates_status ON pdf_ff_templates (status);


-- ---------------------------------------------------------------------------
-- 4. form_run_data — Audit trail for form-filling executions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS form_run_data (
    id              serial       PRIMARY KEY,
    run_id          text         NOT NULL,
    template_id     integer      REFERENCES pdf_ff_templates(id) ON DELETE SET NULL,
    user_id         uuid         REFERENCES users(id) ON DELETE SET NULL,
    form_values     jsonb,
    fill_result     jsonb,
    final_pdf       text,
    status          text         NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'filled', 'partial', 'error', 'submitted')),
    created_at      timestamptz  NOT NULL DEFAULT now(),
    updated_at      timestamptz  NOT NULL DEFAULT now(),
    notes           text
);

COMMENT ON TABLE  form_run_data IS 'Audit trail for every form-filling execution';
COMMENT ON COLUMN form_run_data.run_id IS 'Workflow session identifier (matches session_id from EnergyPlus workflow)';
COMMENT ON COLUMN form_run_data.user_id IS 'UUID of the user whose data was used to fill the form';
COMMENT ON COLUMN form_run_data.form_values IS 'Resolved data values used for filling (pdfField → value)';
COMMENT ON COLUMN form_run_data.fill_result IS 'FF node output: status, fieldsFilled, fieldsMissing, warnings';
COMMENT ON COLUMN form_run_data.final_pdf IS 'Path to filled PDF in Supabase bucket';

CREATE TRIGGER trg_form_run_data_updated_at
    BEFORE UPDATE ON form_run_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_form_run_data_run_id ON form_run_data (run_id);
CREATE INDEX IF NOT EXISTS idx_form_run_data_template ON form_run_data (template_id);
CREATE INDEX IF NOT EXISTS idx_form_run_data_user ON form_run_data (user_id);
CREATE INDEX IF NOT EXISTS idx_form_run_data_status ON form_run_data (status);

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
