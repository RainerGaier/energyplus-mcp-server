# n8n Workflow Examples for EnergyPlus API

**Date:** 2025-01-05 (Updated: 2025-01-06 - Added parameterization)

**Purpose:** Step-by-step examples for building n8n workflows with the EnergyPlus HTTP API

---

## Prerequisites

1. HTTP server running: `python -m energyplus_mcp_server.http_server`
2. ngrok tunnel active: `ngrok http 8000`

---

## Complete Workflow: Site Analysis Pipeline (with Error Handling)

### Workflow Structure

```
Manual Trigger
    → Config (Set node) ← EDIT PARAMETERS HERE BEFORE EACH RUN
    → Health Check → IF (healthy?)
        ├─ Yes → Fetch Weather → IF (weather success?)
        │           ├─ Yes → Generate Model → IF (model success?)
        │           │           ├─ Yes → Run Simulation → IF (sim success?)
        │           │           │           ├─ Yes → Get Results → End
        │           │           │           └─ No → Error: Simulation Failed
        │           │           └─ No → Error: Model Generation Failed
        │           └─ No → Error: Weather Fetch Failed
        └─ No → Error: Server Unavailable
```

### Parameters to Configure Before Running

The **Config** node contains all workflow parameters. Edit these before each run:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `API_BASE_URL` | ngrok URL (can be fetched from Google Sheets) | `https://abc123.ngrok-free.app` |
| `latitude` | Site latitude in decimal degrees | `52.2053` |
| `longitude` | Site longitude in decimal degrees | `0.1218` |
| `location_name` | Name for weather file and site | `Cambridge_UK` |
| `project_name` | Name for the simulation project | `n8n Test Data Center` |
| `building_type` | Type of building template | `data_center` or `manufacturing` |
| `data_center.rack_count` | Number of server racks (data center only) | `25` |
| `data_center.watts_per_rack` | Power per rack in watts (data center only) | `2000` |
| `report_type` | Type of results to retrieve | `summary` or `full` |

---

## Node 1: Manual Trigger

- **Node Type:** Manual Trigger
- **Purpose:** Allows testing the workflow on demand

---

## Node 2: Config (Set Node - Replaces Variables)

**For n8n free tier which doesn't support workflow variables.**

- **Node Type:** Set
- **Name:** Config
- **Mode:** Manual Mapping

### Full Parameterized Config Structure

```json
{
  "API_BASE_URL": "https://your-ngrok-url.ngrok-free.app",
  "last_updated": "2025/01/06 02:02",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "location_name": "Cambridge_UK",
  "project_name": "n8n Test Data Center",
  "building_type": "data_center",
  "data_center": {
    "rack_count": 25,
    "watts_per_rack": 2000
  },
  "report_type": "summary"
}
```

### Config Fields Reference

| Field Name | Type | Description |
|------------|------|-------------|
| `API_BASE_URL` | String | ngrok URL or server base URL |
| `last_updated` | String | Timestamp for tracking config changes |
| `latitude` | Number | Site latitude (decimal degrees) |
| `longitude` | Number | Site longitude (decimal degrees) |
| `location_name` | String | Name for weather file and site identification |
| `project_name` | String | Name for the simulation project |
| `building_type` | String | `data_center` or `manufacturing` |
| `data_center` | Object | Data center specific parameters |
| `data_center.rack_count` | Number | Number of server racks |
| `data_center.watts_per_rack` | Number | Power per rack in watts |
| `report_type` | String | `summary` for condensed results, `full` for detailed |

**Note:** Update `API_BASE_URL` when ngrok restarts. You can also fetch it dynamically from Google Sheets (see Dynamic URL section below).

### Referencing Config in Later Nodes

All subsequent nodes reference the Config node:
```javascript
// Base URL
{{ $('Config').item.json.API_BASE_URL }}/health

// Location parameters
{{ $('Config').item.json.latitude }}
{{ $('Config').item.json.longitude }}
{{ $('Config').item.json.location_name }}

// Project parameters
{{ $('Config').item.json.project_name }}
{{ $('Config').item.json.building_type }}

// Nested data center parameters
{{ $('Config').item.json.data_center.rack_count }}
{{ $('Config').item.json.data_center.watts_per_rack }}
```

---

## Node 3: Health Check

- **Node Type:** HTTP Request
- **Name:** Health Check

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/health` |
| Options → Timeout | 10000 |
| Settings → Continue On Fail | ON |

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-05T12:30:39",
  "energyplus_version": "25.2.0",
  "server_version": "0.1.0"
}
```

---

## Node 4: Check Health (IF Node)

- **Node Type:** IF
- **Name:** Check Health

| Condition | Value |
|-----------|-------|
| Value 1 | `{{ $json.status }}` |
| Operation | equals |
| Value 2 | `healthy` |

**True branch:** Continue to Fetch Weather
**False branch:** Go to Error node

---

## Node 5: Fetch Weather

- **Node Type:** HTTP Request
- **Name:** Fetch Weather

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/weather/fetch` |
| Body Content Type | JSON |
| Settings → Continue On Fail | ON |

**Body (Using Fields Below - references Config parameters):**

| Name | Value |
|------|-------|
| latitude | `{{ $('Config').item.json.latitude }}` |
| longitude | `{{ $('Config').item.json.longitude }}` |
| location_name | `{{ $('Config').item.json.location_name }}` |

**Alternative Body (JSON with expressions):**
```javascript
{
  "latitude": {{ $('Config').item.json.latitude }},
  "longitude": {{ $('Config').item.json.longitude }},
  "location_name": "{{ $('Config').item.json.location_name }}"
}
```

**Expected Response:**
```json
{
  "success": true,
  "epw_path": "C:\\...\\weather_files\\Cambridge_UK_52.2053_0.1218.epw",
  "location": {
    "latitude": 52.2053,
    "longitude": 0.1218,
    "elevation": 10,
    "name": "Cambridge_UK"
  }
}
```

---

## Node 6: Check Weather (IF Node)

- **Node Type:** IF
- **Name:** Check Weather

| Condition | Value |
|-----------|-------|
| Value 1 | `{{ $json.success }}` |
| Operation | equals |
| Value 2 | `true` |

---

## Node 7: Generate Model

- **Node Type:** HTTP Request
- **Name:** Generate Model

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/models/generate` |
| Body Content Type | JSON |
| Settings → Continue On Fail | ON |

**Body (JSON with Config expressions):**
```javascript
{
  "project_name": "{{ $('Config').item.json.project_name }}",
  "location": {
    "latitude": {{ $('Config').item.json.latitude }},
    "longitude": {{ $('Config').item.json.longitude }},
    "site_name": "{{ $('Config').item.json.location_name }}"
  },
  "building_type": "{{ $('Config').item.json.building_type }}",
  "data_center": {
    "rack_count": {{ $('Config').item.json.data_center.rack_count }},
    "watts_per_rack": {{ $('Config').item.json.data_center.watts_per_rack }}
  }
}
```

**Alternative: Using Fields Below**

| Name | Value |
|------|-------|
| project_name | `{{ $('Config').item.json.project_name }}` |
| location.latitude | `{{ $('Config').item.json.latitude }}` |
| location.longitude | `{{ $('Config').item.json.longitude }}` |
| location.site_name | `{{ $('Config').item.json.location_name }}` |
| building_type | `{{ $('Config').item.json.building_type }}` |
| data_center.rack_count | `{{ $('Config').item.json.data_center.rack_count }}` |
| data_center.watts_per_rack | `{{ $('Config').item.json.data_center.watts_per_rack }}` |

**Expected Response:**
```json
{
  "success": true,
  "output_path": "C:\\...\\outputs\\models\\n8n_Test_Data_Center_20250105_140000.idf",
  "template_used": "DataCenter_SingleZone",
  "modifications_applied": [
    "Updated Site:Location to Cambridge_UK (52.2053, 0.1218)",
    "Set IT equipment: 25 units at 2000W each"
  ]
}
```

---

## Node 8: Check Model (IF Node)

- **Node Type:** IF
- **Name:** Check Model

| Condition | Value |
|-----------|-------|
| Value 1 | `{{ $json.success }}` |
| Operation | equals |
| Value 2 | `true` |

---

## Node 9: Run Simulation

- **Node Type:** HTTP Request
- **Name:** Run Simulation

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/simulation/run` |
| Specify Body | Using Fields Below |
| Options → Timeout | 120000 (2 minutes) |
| Settings → Continue On Fail | ON |

**Body Fields:**

| Name | Value |
|------|-------|
| idf_path | `{{ $('Generate Model').item.json.output_path }}` |
| weather_file | `{{ $('Fetch Weather').item.json.epw_path }}` |
| annual | `false` |
| design_day | `true` |

**Note:** For boolean values, toggle to "Expression" mode and enter `false` or `true`.

**Expected Response:**
```json
{
  "success": true,
  "duration_seconds": 1.5,
  "output_directory": "C:\\...\\outputs\\sim_20250105_140030",
  "output_files": {
    "csv": ["eplusout.csv", "eplusMtr.csv"],
    "html": ["eplustbl.htm"],
    "err": ["eplusout.err"]
  }
}
```

---

## Node 10: Check Simulation (IF Node)

- **Node Type:** IF
- **Name:** Check Simulation

| Condition | Value |
|-----------|-------|
| Value 1 | `{{ $json.success }}` |
| Operation | equals |
| Value 2 | `true` |

---

## Node 11: Get Results Summary

- **Node Type:** HTTP Request
- **Name:** Get Results Summary

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/simulation/results/summary` |

**Query Parameters:**

| Name | Value |
|------|-------|
| output_directory | `{{ $('Run Simulation').item.json.output_directory }}` |

**Expected Response:**
```json
{
  "success": true,
  "output_directory": "C:\\...\\outputs\\sim_20250105_140030",
  "simulation_completed": true,
  "energy_summary": {
    "Electricity:Facility [J](Hourly)": {
      "total_J": 123456789,
      "total_kWh": 34.29,
      "total_GJ": 0.123
    }
  },
  "key_metrics": {
    "PUE": 1.42
  },
  "warnings_count": 5,
  "errors_count": 0
}
```

---

## Error Handling Nodes

### Error: Server Unavailable

- **Node Type:** Stop and Error
- **Name:** Error: Server Unavailable
- **Error Message:** `Server health check failed. Check if HTTP server and ngrok are running.`

### Error: Weather Fetch Failed

- **Node Type:** Stop and Error
- **Name:** Error: Weather Fetch Failed
- **Error Message:** `Weather fetch failed: {{ $json.error || $json.detail || 'Unknown error' }}`

### Error: Model Generation Failed

- **Node Type:** Stop and Error
- **Name:** Error: Model Generation Failed
- **Error Message:** `Model generation failed: {{ $json.error || $json.detail || 'Unknown error' }}`

### Error: Simulation Failed

- **Node Type:** Stop and Error
- **Name:** Error: Simulation Failed
- **Error Message:** `Simulation failed: {{ $json.error || $json.detail || 'Unknown error' }}`

---

## Dynamic ngrok URL (Advanced)

Instead of hardcoding the URL in the Config node, you can fetch it dynamically.

### Option A: Fetch from Google Sheets (Recommended for Cloud n8n)

This solves the chicken-and-egg problem where cloud n8n cannot reach localhost.

See [2025-01-06_google-sheets-ngrok-config.md](2025-01-06_google-sheets-ngrok-config.md) for full setup details.

**Workflow Structure with Google Sheets:**
```
Manual Trigger
    → Get ngrok URL (Google Sheets or HTTP Request)
    → Config (Set node with merged parameters)
    → [rest of workflow]
```

**Option A1: Using Google Sheets Node**

- **Node Type:** Google Sheets
- **Operation:** Read Rows
- **Document:** Your EnergyPlus-MCP-Config spreadsheet
- **Sheet:** Sheet1
- **Range:** B1

**Option A2: Using HTTP Request (No API Key Needed)**

- **Node Type:** HTTP Request
- **Name:** Get ngrok URL
- **URL:** `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/gviz/tq?tqx=out:csv&range=B1`

The response body contains just the URL string.

**Merging in Config Node:**

After fetching the URL, use it in your Config Set node:
```javascript
// API_BASE_URL field
{{ $('Get ngrok URL').item.json.values[0][0] }}  // Google Sheets node
// or
{{ $json }}  // HTTP Request with CSV export
```

### Option B: Fetch from Local ngrok API (if n8n runs on same machine)

Add a node before Config:

- **Node Type:** HTTP Request
- **Name:** Get ngrok URL
- **URL:** `http://127.0.0.1:4040/api/tunnels`

Then in Config node:
```javascript
{{ $('Get ngrok URL').item.json.tunnels[0].public_url }}
```

### Option C: Fetch from Server Config Endpoint

The server provides an endpoint that auto-detects the ngrok URL:

- **Node Type:** HTTP Request
- **Name:** Get API URL
- **URL:** `http://localhost:8000/api/config/ngrok-url`

**Response:**
```json
{
  "success": true,
  "ngrok_url": "https://abc123.ngrok-free.app",
  "source": "ngrok_api"
}
```

Then use: `{{ $('Get API URL').item.json.ngrok_url }}`

### Option D: Update URL via POST

When ngrok restarts, update the server's config:

```bash
curl -X POST "http://localhost:8000/api/config/ngrok-url?url=https://new-url.ngrok-free.app"
```

---

## Alternative Workflow Nodes

### Get Full Results

For more detailed results including file listings and warnings:

- **Node Type:** HTTP Request
- **Name:** Get Full Results

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/simulation/results` |

**Query Parameters:**

| Name | Value |
|------|-------|
| output_directory | `{{ $('Run Simulation').item.json.output_directory }}` |
| include_timeseries | `false` |

Set `include_timeseries` to `true` to get raw CSV data (can be large).

---

### Read Specific Output File

To read contents of a specific file:

- **Node Type:** HTTP Request
- **Name:** Read Output File

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/files/read` |

**Query Parameters:**

| Name | Value |
|------|-------|
| file_path | Full path to the file |
| max_lines | `1000` |

---

## Manufacturing Facility Example

Alternative body for **Generate Model** node:

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

## List Available Templates

Standalone node to see what templates are available:

- **Node Type:** HTTP Request
- **Name:** List Templates

| Setting | Value |
|---------|-------|
| Method | GET |
| URL | `{{ $('Config').item.json.API_BASE_URL }}/api/templates` |

Optional query parameter: `building_type=data_center` or `building_type=manufacturing`

---

## Expression Syntax Reference

### Accessing Config Node

```javascript
// Get API base URL from Config node
{{ $('Config').item.json.API_BASE_URL }}

// Combine with endpoint path
{{ $('Config').item.json.API_BASE_URL }}/api/templates
```

### Accessing Previous Node Data

```javascript
// Get output_path from Generate Model node
{{ $('Generate Model').item.json.output_path }}

// Get epw_path from Fetch Weather node
{{ $('Fetch Weather').item.json.epw_path }}

// Get output_directory from Run Simulation node
{{ $('Run Simulation').item.json.output_directory }}
```

### Conditional Logic

```javascript
// Check if simulation succeeded
{{ $json.success ? 'Completed' : 'Failed' }}

// Get error message with fallback
{{ $json.error || $json.detail || 'Unknown error' }}
```

---

## Troubleshooting

### "JSON parameter needs to be valid JSON"

- Use "Using Fields Below" instead of JSON body
- Or ensure expressions start with `=` in Expression mode

### Windows Path Issues

- The API handles Windows backslashes internally
- Use "Using Fields Below" for paths from previous nodes

### Timeout Errors

- Set HTTP Request node timeout to 120000ms (2 minutes) for simulations
- Design day simulations are faster than annual

### ngrok URL Changed

1. Update the Config node with the new URL
2. Or use the dynamic URL approach (Option B above)
3. Or update via POST: `curl -X POST "http://localhost:8000/api/config/ngrok-url?url=NEW_URL"`

### Workflow Fails at IF Node

- Ensure "Continue On Fail" is enabled on HTTP Request nodes
- Check that the condition matches the actual response field

---

## API Endpoints Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/config/ngrok-url` | GET | Get current ngrok URL |
| `/api/config/ngrok-url` | POST | Update ngrok URL |
| `/api/weather/fetch` | POST | Fetch EPW weather file |
| `/api/templates` | GET | List building templates |
| `/api/templates/{id}` | GET | Get template details |
| `/api/models/generate` | POST | Generate IDF from spec |
| `/api/simulation/run` | POST | Run simulation |
| `/api/simulation/results` | GET | Get full results |
| `/api/simulation/results/summary` | GET | Get condensed summary |
| `/api/files/read` | GET | Read output file contents |
