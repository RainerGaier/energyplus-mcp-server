# Testing sequence

All three workflows are created. Here's a summary of what's been built and what you need to do next for testing.

---

Files Created / Updated

| File | Status | Description |
|------|--------|-------------|
| n8n/Add_Form-Template v0.1.json | New | Template cataloguing workflow |
| n8n/Fill_Form v0.1.json | New | Reusable form-filling sub-workflow |
| n8n/EnergyPlus v0.5.json | New | Extended simulation workflow with form-filling |
| n8n/README.md | Updated | Added all three new workflows + documentation |
| roadmap/planning/CR-001-form-handling-integration.md | Updated | Phase 1 marked complete |
| roadmap/planning/CR-001-database-schema.sql | Updated | Marked as APPLIED |


---

### Before You Can Test

There are 3 setup steps needed in your local n8n after importing the workflows:

- Configure Supabase API credentials — All three workflows reference "id": "CONFIGURE_ME" on their Supabase nodes. You need to:
- Create a Supabase API credential in n8n (Settings > Credentials > Add > Supabase)
- Use the service_role key from your .env
- Update each Supabase node to point to that credential
- Upload PDF binary for Add Form Template — The Manual Trigger doesn't include a PDF binary. For testing, you'll need to either:
- Add a "Read Binary File" node before "Validate & Merge Config" pointing to a test PDF (e.g. the UKPN G98 from n8n-nodes-pdf-form-filler/test/fixtures/)
- Or use the webhook with a multipart form upload
- Create a test user record — The Fill Form workflow needs a valid user_id in the users table. Check if any test users already exist.
  

---

### Testing Order

**Add Form Template first** — catalogue a PDF, verify fields are discovered and stored
**Manually map some fields** in the pdf_ff_templates.source_to_template_mapping column via Supabase dashboard
**Fill Form standalone** — test with the catalogued template + a real user_id
**EnergyPlus v0.5** end-to-end — only after the above work

