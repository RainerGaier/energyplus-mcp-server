# n8n Integration Guide

This guide explains how to integrate the EnergyPlus HTTP API with n8n workflows.

## Starting the HTTP Server

```bash
# From the project directory
cd energyplus-mcp-server

# Start the server
python -m energyplus_mcp_server.http_server

# Or with uvicorn directly
uvicorn energyplus_mcp_server.http_server:app --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, you can access:
- **Interactive API docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative docs**: http://localhost:8000/redoc (ReDoc)

## Available Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API root - returns server info |
| `/health` | GET | Health check for monitoring |

### Weather Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/weather/fetch` | POST | Fetch weather data for a location |
| `/api/weather/coverage` | GET | Get weather data coverage info |
| `/api/weather/check-coverage` | GET | Check coverage for specific location |

### Building Templates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/templates` | GET | List available building templates |
| `/api/templates/{template_id}` | GET | Get details of a specific template |
| `/api/schemas/building-specification` | GET | Get the building specification schema |

### Model Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/models/generate` | POST | Generate customized IDF model |
| `/api/models/info` | GET | Get information about an IDF model |
| `/api/models/zones` | GET | List zones in an IDF model |
| `/api/models/validate` | GET | Validate an IDF model |

### Simulation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/simulation/run` | POST | Run EnergyPlus simulation |
| `/api/simulation/status` | GET | Get simulation status |

### Files

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/available` | GET | List available sample files |

---

## n8n Workflow Examples

### Example 1: Complete Site Analysis Workflow

This workflow demonstrates the full pipeline:
1. Receive site coordinates
2. Fetch weather data
3. Generate building model
4. Run simulation

#### Step 1: Webhook Trigger (receives site data)

Configure an n8n Webhook node to receive:
```json
{
  "site_name": "Cambridge Data Center",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "building_type": "data_center",
  "it_load_kw": 100
}
```

#### Step 2: Fetch Weather (HTTP Request node)

- **Method**: POST
- **URL**: `http://localhost:8000/api/weather/fetch`
- **Body Type**: JSON
- **Body**:
```json
{
  "latitude": {{ $json.latitude }},
  "longitude": {{ $json.longitude }},
  "location_name": "{{ $json.site_name }}"
}
```

#### Step 3: Generate Building Model (HTTP Request node)

- **Method**: POST
- **URL**: `http://localhost:8000/api/models/generate`
- **Body Type**: JSON
- **Body**:
```json
{
  "project_name": "{{ $('Webhook').item.json.site_name }}",
  "location": {
    "latitude": {{ $('Webhook').item.json.latitude }},
    "longitude": {{ $('Webhook').item.json.longitude }},
    "site_name": "{{ $('Webhook').item.json.site_name }}"
  },
  "building_type": "{{ $('Webhook').item.json.building_type }}",
  "data_center": {
    "it_load_kw": {{ $('Webhook').item.json.it_load_kw }}
  }
}
```

#### Step 4: Run Simulation (HTTP Request node)

- **Method**: POST
- **URL**: `http://localhost:8000/api/simulation/run`
- **Body Type**: JSON
- **Body**:
```json
{
  "idf_path": "{{ $json.output_path }}",
  "weather_file": "{{ $('Fetch Weather').item.json.epw_path }}",
  "annual": false,
  "design_day": true
}
```

---

### Example 2: List Templates Workflow

Simple workflow to retrieve available templates:

#### HTTP Request Node

- **Method**: GET
- **URL**: `http://localhost:8000/api/templates`
- **Query Parameters** (optional):
  - `building_type`: `data_center` or `manufacturing`

---

### Example 3: Manufacturing Facility Analysis

#### Generate Manufacturing Model

- **Method**: POST
- **URL**: `http://localhost:8000/api/models/generate`
- **Body**:
```json
{
  "project_name": "Fenland Manufacturing",
  "location": {
    "latitude": 52.4667,
    "longitude": 0.1500,
    "site_name": "Fenland_Industrial"
  },
  "building_type": "manufacturing",
  "manufacturing": {
    "process_load_kw": 150,
    "process_heat_fraction": 0.6,
    "occupancy_count": 25
  }
}
```

---

## Response Formats

### Weather Fetch Response
```json
{
  "success": true,
  "epw_path": "C:\\...\\weather_files\\Cambridge_UK.epw",
  "location": {
    "latitude": 52.2053,
    "longitude": 0.1218,
    "elevation": 10,
    "name": "Cambridge_UK"
  },
  "metadata": {
    "source": "PVGIS-SARAH2",
    "years": "2005-2020"
  }
}
```

### Model Generation Response
```json
{
  "success": true,
  "output_path": "C:\\...\\outputs\\models\\Cambridge_DC_20250105.idf",
  "template_used": "DataCenter_SingleZone",
  "modifications_applied": [
    "Updated Site:Location to Cambridge_UK (52.2053, 0.1218)",
    "Set IT equipment: 50 units at 2000W each"
  ],
  "timestamp": "2025-01-05T12:30:00"
}
```

### Simulation Run Response
```json
{
  "success": true,
  "duration_seconds": 1.5,
  "output_directory": "C:\\...\\outputs\\sim_20250105_123000",
  "output_files": {
    "csv": ["eplusout.csv"],
    "html": ["eplustbl.htm"],
    "err": ["eplusout.err"]
  },
  "warnings": 0,
  "errors": 0
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

HTTP Status Codes:
- `200`: Success
- `400`: Bad request (invalid input)
- `404`: Resource not found
- `500`: Server error

---

## n8n Node Configuration Tips

### HTTP Request Node Settings

1. **Authentication**: Not required for local development
2. **Timeout**: Set to 120000ms (2 minutes) for simulations
3. **Error Handling**: Enable "Continue On Fail" to handle errors gracefully

### Expression Examples

```javascript
// Access nested JSON
{{ $json.location.latitude }}

// Reference previous node output
{{ $('Previous Node').item.json.output_path }}

// Conditional logic
{{ $json.success ? $json.output_path : 'Error' }}
```

---

## Production Deployment

For production use:

1. **Set environment variables**:
   ```bash
   export ENERGYPLUS_PATH=/path/to/EnergyPlusV25-2-0
   ```

2. **Run with production server**:
   ```bash
   uvicorn energyplus_mcp_server.http_server:app \
     --host 0.0.0.0 \
     --port 8000 \
     --workers 4
   ```

3. **Configure CORS** (if needed): Edit `http_server.py` to restrict `allow_origins`

4. **Add authentication**: Consider adding API key authentication for production

---

## Troubleshooting

### Server Won't Start
- Ensure EnergyPlus is installed
- Check that port 8000 is available
- Verify Python dependencies: `pip install -e .`

### Simulation Fails
- Check EnergyPlus path configuration
- Verify IDF and EPW file paths exist
- Review the EnergyPlus error log in the output directory

### Weather Fetch Fails
- Verify internet connection
- Check that coordinates are within PVGIS coverage
- Some remote locations may only have ERA5 data

---

## Integration with Rob's Components

This HTTP API is designed to receive inputs from the site selection phase:

```
Site Selection (Rob)
    → Webhook with lat/long
    → /api/weather/fetch
    → /api/models/generate
    → /api/simulation/run
    → Return results to orchestrator
```

The building specification schema aligns with the orchestrator's expected format.
