-- CR-003: Sync system_config with actual data keys from user_details and pdf_ff_templates
-- Run ad-hoc in Supabase SQL Editor whenever you want to register new data keys
-- that were created by Generate Synthetic Data or manual Extended Info edits.
--
-- What it does:
--   1. Collects all registered field keys from system_config
--   2. Collects all dataKey values from pdf_ff_templates.source_to_template_mapping
--      where source = 'user_details'
--   3. Collects all actual keys from user_details.details JSONB
--   4. Finds keys present in (2) or (3) but missing from (1)
--   5. Appends them to system_config.setting.fields[] with sensible defaults
--   6. Reports what was added
--
-- Safe to run multiple times (idempotent) — only adds keys that don't exist yet.
-- Does NOT remove keys — only grows the registry.

DO $$
DECLARE
    v_current_fields  jsonb;
    v_registered_keys text[];
    v_mapping_keys    text[];
    v_details_keys    text[];
    v_all_new_keys    text[];
    v_key             text;
    v_new_field       jsonb;
    v_label           text;
    v_added           text[] := '{}';
BEGIN
    -- ─── Step 1: Get currently registered keys ───
    SELECT setting->'fields'
    INTO v_current_fields
    FROM system_config
    WHERE parameter = 'user_details';

    IF v_current_fields IS NULL THEN
        RAISE EXCEPTION 'system_config row with parameter=user_details not found';
    END IF;

    SELECT array_agg(f->>'key')
    INTO v_registered_keys
    FROM jsonb_array_elements(v_current_fields) AS f;

    v_registered_keys := COALESCE(v_registered_keys, '{}');

    RAISE NOTICE '── Currently registered keys (%) ──', array_length(v_registered_keys, 1);
    RAISE NOTICE '%', v_registered_keys;

    -- ─── Step 2: Collect dataKeys from all template mappings (source=user_details) ───
    SELECT COALESCE(array_agg(DISTINCT m->>'dataKey'), '{}')
    INTO v_mapping_keys
    FROM pdf_ff_templates t,
         jsonb_array_elements(t.source_to_template_mapping) AS m
    WHERE m->>'source' = 'user_details'
      AND m->>'dataKey' IS NOT NULL
      AND m->>'dataKey' != '';

    RAISE NOTICE '── Keys from template mappings (source=user_details): % ──', array_length(v_mapping_keys, 1);
    RAISE NOTICE '%', v_mapping_keys;

    -- ─── Step 3: Collect all keys from user_details.details JSONB ───
    SELECT COALESCE(array_agg(DISTINCT k), '{}')
    INTO v_details_keys
    FROM user_details ud,
         jsonb_object_keys(ud.details) AS k;

    RAISE NOTICE '── Keys from user_details.details: % ──', array_length(v_details_keys, 1);
    RAISE NOTICE '%', v_details_keys;

    -- ─── Step 4: Find new keys (in mappings or details, but not registered) ───
    SELECT COALESCE(array_agg(DISTINCT k), '{}')
    INTO v_all_new_keys
    FROM (
        SELECT unnest(v_mapping_keys) AS k
        UNION
        SELECT unnest(v_details_keys) AS k
    ) combined
    WHERE k != ''
      AND k != ANY(v_registered_keys) IS NOT TRUE;

    -- Filter out keys already registered (the NOT TRUE handles NULLs)
    SELECT COALESCE(array_agg(k), '{}')
    INTO v_all_new_keys
    FROM unnest(v_all_new_keys) AS k
    WHERE NOT (k = ANY(v_registered_keys));

    IF array_length(v_all_new_keys, 1) IS NULL OR array_length(v_all_new_keys, 1) = 0 THEN
        RAISE NOTICE '';
        RAISE NOTICE '✓ No new keys to add — system_config is up to date.';
        RETURN;
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '── New keys to register: % ──', array_length(v_all_new_keys, 1);
    RAISE NOTICE '%', v_all_new_keys;

    -- ─── Step 5: Append each new key to system_config.setting.fields[] ───
    FOREACH v_key IN ARRAY v_all_new_keys
    LOOP
        -- Build a human-readable label from the key: site_address → Site Address
        v_label := initcap(replace(v_key, '_', ' '));

        v_new_field := jsonb_build_object(
            'key',      v_key,
            'label',    v_label,
            'type',     'text',
            'required', false,
            'source',   'user_details'
        );

        v_current_fields := v_current_fields || jsonb_build_array(v_new_field);
        v_added := array_append(v_added, v_key);

        RAISE NOTICE '  + Added: % (label: "%", source: user_details)', v_key, v_label;
    END LOOP;

    -- ─── Step 6: Write back to system_config ───
    UPDATE system_config
    SET setting = jsonb_set(setting, '{fields}', v_current_fields),
        description = setting->>'description'
                      || ' | CR-003 sync: added '
                      || array_length(v_added, 1)::text
                      || ' keys on '
                      || now()::date::text
    WHERE parameter = 'user_details';

    RAISE NOTICE '';
    RAISE NOTICE '✓ system_config updated — added % new field(s):', array_length(v_added, 1);
    RAISE NOTICE '%', v_added;
END;
$$;

-- ─── Verify: show all registered fields after sync ───
SELECT
    f->>'key'      AS key,
    f->>'label'    AS label,
    f->>'source'   AS source,
    f->>'type'     AS type,
    f->>'required' AS required
FROM system_config,
     jsonb_array_elements(setting->'fields') AS f
WHERE parameter = 'user_details'
ORDER BY f->>'source', f->>'key';
