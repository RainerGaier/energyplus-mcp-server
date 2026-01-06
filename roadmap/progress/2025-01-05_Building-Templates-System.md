# Progress Note: Building Templates System

**Date:** 2025-01-05

**Milestone:** 1 - Foundation / 2 - Building Templates

**Status:** Initial Implementation Complete

---

## Summary

Implemented a building template system that allows generating customized EnergyPlus IDF files from high-level building specifications. This enables the workflow:

```
Site Selection (Rob) → Building Spec → Template Service → IDF Model → Simulation
```

---

## Components Created

### 1. Template Directory Structure

```
templates/
└── data_center/
    ├── DataCenter_SingleZone.idf    # Base IDF template
    └── DataCenter_SingleZone.json   # Metadata & parameters
```

### 2. Template Metadata (`DataCenter_SingleZone.json`)

Defines:
- Default parameter values (geometry, IT equipment, HVAC, setpoints)
- Parameterizable fields with valid ranges
- IDF locations for each modifiable parameter
- Custom output variables (PUE, SCOP)

### 3. Building Specification Schema (`schemas/building_specification.json`)

JSON Schema defining inputs from the orchestrator:

| Required Field | Description |
|---------------|-------------|
| `location` | `{latitude, longitude, site_name}` |
| `building_type` | `data_center`, `manufacturing`, etc. |

| Optional Fields | Description |
|-----------------|-------------|
| `geometry` | Dimensions, floor area, orientation |
| `data_center` | IT load, rack count, target PUE |
| `manufacturing` | Process type, loads, occupancy |
| `setpoints` | Heating/cooling temperatures |
| `simulation_options` | Annual vs design day runs |

### 4. Template Service (`energyplus_mcp_server/utils/template_service.py`)

Core functionality:
- `list_templates()` - List available templates
- `get_template()` - Get template metadata
- `generate_model()` - Apply specification to template

Modifications supported:
- Location (latitude, longitude, timezone, elevation)
- Geometry scaling (length, width, height)
- IT equipment (rack count, watts per rack)
- Temperature setpoints
- Simulation options

### 5. MCP Tools Added

| Tool | Purpose |
|------|---------|
| `list_building_templates` | List available templates with metadata |
| `get_template_details` | Get full parameter information |
| `generate_building_model` | Create customized IDF from spec |
| `get_building_specification_schema` | Return the input schema |

---

## Testing

### Test 1: Template Service Initialization
```
Templates found: 1
  - DataCenter_SingleZone: Single Zone Data Center with CRAC Cooling
```

### Test 2: Model Generation
```python
building_spec = {
    'project_name': 'Cambridge Test DC',
    'location': {'latitude': 52.2053, 'longitude': 0.1218},
    'building_type': 'data_center',
    'data_center': {'rack_count': 50, 'watts_per_rack': 2000}
}
```

**Result:**
```json
{
  "success": true,
  "output_path": "outputs/models/cambridge_test.idf",
  "template_used": "DataCenter_SingleZone",
  "modifications_applied": [
    "Updated Site:Location to Cambridge_UK (52.2053, 0.1218)",
    "Set IT equipment: 50 units at 2000W each",
    "Set cooling setpoint to 27.0°C"
  ]
}
```

---

## Workflow Integration

### From Orchestrator (Rob's Components)

```python
# 1. Receive site selection output
site = {
    "latitude": 52.2053,
    "longitude": 0.1218,
    "catchment": "Cam and Ely Ouse"
}

# 2. Fetch weather
weather_result = await fetch_weather_by_location(
    site["latitude"], site["longitude"], "Cambridge_UK"
)

# 3. Generate building model
model_result = await generate_building_model(json.dumps({
    "project_name": "Cambridge Data Center",
    "location": site,
    "building_type": "data_center",
    "data_center": {"it_load_kw": 100}
}))

# 4. Run simulation
sim_result = await run_simulation(
    model_result["output_path"],
    weather_file=weather_result["epw_path"]
)
```

---

## Files Changed/Created

| File | Status | Description |
|------|--------|-------------|
| `templates/data_center/DataCenter_SingleZone.idf` | New | Base data center template |
| `templates/data_center/DataCenter_SingleZone.json` | New | Template metadata |
| `schemas/building_specification.json` | New | Input schema definition |
| `energyplus_mcp_server/utils/template_service.py` | New | Template service class |
| `energyplus_mcp_server/server.py` | Modified | Added 4 new MCP tools |

---

## Limitations & Future Work

### Current Limitations

1. **Geometry scaling** - Simplified approach using coordinate multiplication
2. **Design days** - Still uses Denver design days (need location-specific)
3. **Single template** - Only DataCenter_SingleZone available

### Next Steps

1. Add more templates (Warehouse_Manufacturing, Office_Small)
2. Implement proper design day generation based on location
3. Add HVAC system swapping capability
4. Integrate with weather lookup for automatic weather file selection

---

## Manufacturing/Warehouse Template (Added Later)

### Template Details

| Property | Value |
|----------|-------|
| **Template ID** | `Manufacturing_Warehouse` |
| **Source** | DOE Commercial Reference Building (RefBldgWarehouseNew2004) |
| **Floor Area** | 4,835 m² (52,045 ft²) |
| **Zones** | 3 (BulkStorage 66%, FineStorage 29%, Office 5%) |
| **Height** | 8.5m clear height |
| **HVAC** | Gas unit heaters (storage) + PSZ-AC (office) |

### Directory Structure Update

```
templates/
├── data_center/
│   ├── DataCenter_SingleZone.idf
│   └── DataCenter_SingleZone.json
└── manufacturing/
    ├── Manufacturing_Warehouse.idf
    └── Manufacturing_Warehouse.json
```

### Manufacturing-Specific Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `process_load_kw` | float | Process equipment electrical load (adds ElectricEquipment object) |
| `process_heat_fraction` | float | Fraction of load becoming radiant heat (default 0.5) |
| `occupancy_count` | integer | Number of workers in facility |

### Test: Manufacturing Model Generation

```python
building_spec = {
    'project_name': 'Cambridge Manufacturing',
    'location': {'latitude': 52.2053, 'longitude': 0.1218},
    'building_type': 'manufacturing',
    'manufacturing': {
        'process_load_kw': 150,
        'process_heat_fraction': 0.6,
        'occupancy_count': 25
    }
}
```

**Result:**
```json
{
  "success": true,
  "output_path": "outputs/models/cambridge_manufacturing.idf",
  "template_used": "Manufacturing_Warehouse",
  "modifications_applied": [
    "Updated Site:Location to Cambridge_UK_Manufacturing (52.2053, 0.1218)",
    "Added process equipment load: 150.0 kW (60% radiant heat)",
    "Note: Occupancy specified as 25 people (requires manual IDF adjustment)"
  ]
}
```

### Generated IDF Additions

The template service automatically inserts process equipment:

```
ElectricEquipment,
  BulkStorage_ProcessLoad, !- Name
  BulkStorage,             !- Zone or ZoneList Name
  BLDG_EQUIP_SCH,          !- Schedule Name
  EquipmentLevel,          !- Design Level Calculation Method
  150000.0,                !- Design Level {W}
  ,                        !- Watts per Zone Floor Area {W/m2}
  ,                        !- Watts per Person {W/person}
  0,                       !- Fraction Latent
  0.60,                    !- Fraction Radiant
  0,                       !- Fraction Lost
  Manufacturing Process Equipment;  !- End-Use Subcategory
```

### Use Cases

- Light manufacturing facilities
- Distribution centers
- Warehouses with office space
- Assembly plants
- Storage facilities with climate control requirements

---

## Available Templates Summary

| Template ID | Building Type | Floor Area | HVAC System |
|-------------|--------------|------------|-------------|
| `DataCenter_SingleZone` | data_center | 232 m² | CRAC + DX Cooling |
| `Manufacturing_Warehouse` | manufacturing, warehouse | 4,835 m² | Gas Heaters + PSZ-AC |

---

## Milestone Status Update

### Milestone 1: Foundation
- [x] Fix cross-platform configuration
- [x] Integrate weather file lookup by lat/long
- [x] Design building specification input schema ← **COMPLETED**

### Milestone 2: Building Templates
- [x] Create initial template structure
- [x] Implement parametric model generation
- [x] Add Manufacturing_Warehouse template ← **COMPLETED**
- [x] Define default parameters for deterministic first runs
- [ ] Add Office_Small template

---

## HTTP API for n8n Integration (Added Later)

### Overview

Added a FastAPI HTTP server to expose MCP tools as REST endpoints for n8n workflow integration.

### New File: `energyplus_mcp_server/http_server.py`

FastAPI application with endpoints for:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API root - server info |
| `/health` | GET | Health check |
| `/api/weather/fetch` | POST | Fetch EPW weather file |
| `/api/weather/coverage` | GET | Check data coverage |
| `/api/templates` | GET | List building templates |
| `/api/templates/{id}` | GET | Get template details |
| `/api/models/generate` | POST | Generate IDF from spec |
| `/api/simulation/run` | POST | Run EnergyPlus simulation |

### Running the Server

```bash
# Start the HTTP server
python -m energyplus_mcp_server.http_server

# Or with uvicorn
uvicorn energyplus_mcp_server.http_server:app --host 0.0.0.0 --port 8000
```

### API Documentation

When the server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Test Results

```bash
# Health check
curl http://localhost:8000/health
{"status":"healthy","timestamp":"2025-01-05T12:30:39","energyplus_version":"25.2.0"}

# List templates
curl http://localhost:8000/api/templates
{"success":true,"count":2,"templates":[...]}

# Generate model
curl -X POST http://localhost:8000/api/models/generate \
  -H "Content-Type: application/json" \
  -d '{"location":{"latitude":52.2053,"longitude":0.1218},"building_type":"data_center"}'
{"success":true,"output_path":"...","template_used":"DataCenter_SingleZone"}
```

### Dependencies Added

```toml
# pyproject.toml
dependencies = [
    ...
    "fastapi",
    "uvicorn[standard]",
    "pydantic>=2.0"
]
```

### Documentation

See [docs/n8n-integration.md](../docs/n8n-integration.md) for complete n8n workflow examples.

### Milestone 4: Integration (Partial)
- [x] Add HTTP API endpoints for n8n
- [x] Document API for workflow integration
- [ ] Define full API/interface for orchestrator
- [ ] Implement GCS integration for file storage
- [ ] Containerize for cloud deployment
