# Phase 1 Approach: Technical Models (3.0)

**Lead:** Rainer

**Last Updated:** 2025-01-05

---

## Project Context

This EnergyPlus MCP Server is part of a larger **Stakeholder-Informed Rapid Site Selection & Technical Modelling Agentic System**. The system pipeline:

```
1.0 Site Selection (Rob)
    ↓
2.0 Stakeholder Preparation (Rob)
    ↓
3.0 Technical Models (Rainer) ← WE ARE HERE
    ↓
4.0 Stakeholder Feedback (Rob)
    ↓
5.0 Design Adjustments (Rainer + Rob)
    ↓
6.0 Iteration Loop
    ↓
7.0 Stakeholder Material Creation (Rob + Andy)
```

### Team

- **Rainer** (South Africa) - Technical Models
- **Rob** (UK) - Site Selection, Stakeholder Analysis, Orchestration

---

## Phase 1 Scope

### Models to Implement

1. Energy Models (EnergyPlus / OpenStudio)
2. HVAC / Mechanical
3. Electrical
4. BIM Models (Blender / Bonsai)

### Future Phases

- **Phase 2:** Plumbing/Water (QSDsan), Renewable Models
- **Phase 3:** Nature-based solutions, Constructed wetlands, Quarry lake cooling

---

## Technical Approach

### Input/Output Flow

```
INPUT:
  - Location (lat/long) from Site Selection
  - Building specification (type, size, floors, occupancy, etc.)

PROCESSING:
  - Fetch weather file (EPW) for location
  - Select/generate appropriate building model
  - Run EnergyPlus simulation
  - Process results

OUTPUT:
  - Technical reports for stakeholder review
```

### Key Design Decisions

| Decision               | Approach                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| **Building Models**    | Use standardized templates (DOE prototypes or similar) with modifiable parameters            |
| **First Run**          | Deterministic with fixed defaults for consistency                                            |
| **Iteration Strategy** | Hybrid - regenerate for major changes (location/type), tweak for minor parameter adjustments |
| **Deployment**         | Local development → Google Cloud with GCS for storage                                        |

---

## Current State Assessment

| Capability                      | Status      | Notes                                                    |
| ------------------------------- | ----------- | -------------------------------------------------------- |
| Load/run EnergyPlus models      | ✅ Working  | Tested with 1ZoneDataCenterCRAC_wPumpedDXCoolingCoil.idf |
| Weather file handling           | ✅ Working  | PVGIS API integration, lat/long → EPW lookup             |
| Standardized building templates | ✅ Working  | DataCenter_SingleZone template with metadata             |
| Parameterized model generation  | ✅ Working  | TemplateService generates customized IDFs                |
| Structured report generation    | ⚠️ Basic   | Raw CSV/HTML only                                        |
| 3D geometry export              | ✅ Working  | IDF → OBJ/glTF via GeomEppy + Trimesh                    |
| Cloud storage (Supabase)        | ✅ Working  | Supabase storage bucket integration                      |
| Building specification schema   | ✅ Working  | JSON schema with examples                                |
| Cross-platform config           | ✅ Working  | Auto-detects platform, env vars supported                |

---

## Phase 1 Roadmap

### Milestone 1: Foundation ✅ Complete

- [x] Fix cross-platform configuration (Windows + Linux/Docker)
- [x] Design building specification input schema
- [x] Integrate weather file lookup by lat/long coordinates

### Milestone 2: Building Templates (In Progress)

- [x] Source/create standardized building templates (DataCenter_SingleZone)
- [x] Implement parameterized model generation (TemplateService)
- [x] Define default parameters for deterministic first runs
- [ ] Add additional templates (Warehouse_Manufacturing, Office_Small)

### Milestone 3: 3D Visualization Export ✅ Complete

- [x] Implement IDF → OBJ geometry extraction (GeomEppy)
- [x] Implement OBJ → glTF conversion (Trimesh)
- [x] Add `/api/export/3d` HTTP endpoint
- [x] Support Blender-compatible formats for BIM visualization

### Milestone 4: File Download API ✅ Complete

- [x] Add `/api/files/download` endpoint for binary file downloads
- [x] Add `/api/files/list` endpoint to list folder contents
- [x] Enable n8n workflows to download files and upload to Google Drive (via Rob's OAuth)

### Milestone 5: Supabase Storage Export ✅ Complete

- [x] Add Supabase storage service for uploading simulation files
- [x] Add `/api/export/supabase` HTTP endpoint
- [x] Support folder creation and file replacement in bucket
- [x] Return bucket name and folder path on success

### Milestone 6: Reporting

- [ ] Design structured technical report format
- [ ] Implement report generation from simulation results

### Milestone 7: Integration

- [ ] Define API/interface for receiving inputs from orchestrator
- [ ] Implement GCS integration for file storage
- [ ] Containerize for cloud deployment

---

## Orchestration Options (TBD)

Two approaches under consideration:

1. **Master MCP Server** - An overarching MCP that handles orchestration between components
2. **External Orchestrator (n8n)** - Use n8n to handle inputs/outputs and agent initiations

Decision pending discussion with Rob.

---

## Open Questions

1. ~~**Weather File Lookup** - Which service to use?~~ → **Resolved**: Using PVGIS API
2. **Building Templates** - ~~Use DOE Commercial Reference Buildings? Need manufacturing prototypes?~~ → **Researched**: See `roadmap/research/2025-01-05_OpenStudio-Measures-Assessment.md`
3. **Input Schema** - What fields are required for building specification?
4. **Integration Protocol** - How will Rob's components communicate with this MCP?

---

## Building Templates Strategy

Based on OpenStudio Measures research (see [assessment](research/2025-01-05_OpenStudio-Measures-Assessment.md)):

### Approach: Hybrid (IDF Templates + Python Parametric Tools)

**Phase 1 (Current):**
- Extract IDF templates from OpenStudio measures and existing samples
- Store as seed models in `/templates` folder
- Python tools for basic parameter modifications

**Phase 2 (Future):**
- Add full OpenStudio integration for complex regeneration scenarios
- Leverage BCL measures for HVAC system variations

### Priority Templates

| Template | Source | HVAC System | Status |
|----------|--------|-------------|--------|
| DataCenter_SingleZone | Existing sample | CRAC w/ DX Cooling | ✅ Available |
| Manufacturing_Warehouse | DOE RefBldg | Gas Unit Heaters + PSZ-AC | ✅ Available |
| DataCenter_MultiZone | Custom | Chilled Water + CRAC | To create |
| Office_Small | DOE Prototype | Packaged rooftop | To extract |

### Gaps Identified

- No explicit manufacturing facility prototype in BCL
- DOE prototypes are US-focused (may need UK/EU adaptations)
- Industrial process loads require custom development

---

## Environment Setup

### Local Development (Windows)

- EnergyPlus 25.2.0 installed at `C:\EnergyPlusV25-2-0`
- Python 3.13 with dependencies installed via `pip install -e .`
- **No environment variables required** - auto-detects EnergyPlus installation
- Optional: Copy `.env.example` to `.env` for custom paths

### Docker/Devcontainer (Linux)

- EnergyPlus at `/app/software/EnergyPlusV25-2-0`
- Configured in `.devcontainer/devcontainer.json`

---

## Test Results

**Date:** 2025-01-05

**Model:** 1ZoneDataCenterCRAC_wPumpedDXCoolingCoil.idf

**Result:** ✅ Simulation completed successfully (design day, ~1.5s)

**Output:** 19 files generated including CSV time-series, HTML reports, SQLite database

---

## References

- [EnergyPlus Documentation](https://energyplus.net/documentation)
- [DOE Commercial Reference Buildings](https://www.energy.gov/eere/buildings/commercial-reference-buildings)
- [Climate.OneBuilding.Org Weather Files](https://climate.onebuilding.org/)
- [PVGIS API Documentation](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en)
- [BCL - Building Component Library](https://bcl.nrel.gov/)
- [OpenStudio Measure Writing Guide](https://nrel.github.io/OpenStudio-user-documentation/reference/measure_writing_guide/)
- [eppy - Python IDF Editor](https://eppy.readthedocs.io/)
- Project concept document: `concept.md`