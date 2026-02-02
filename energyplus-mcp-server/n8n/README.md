# n8n Workflows for EnergyPlus MCP

This folder contains n8n workflow definitions for the EnergyPlus MCP Server.

## Workflows

| Workflow | Purpose | Environment |
|----------|---------|-------------|
| `EnergyPlus Test v0.1.json` | Development/testing with ngrok | Local + ngrok |
| `EnergyPlus GCP v1.0.json` | Production on GCP VM | GCP VM |

---

## EnergyPlus Test v0.1 (Local Development)

**Use when:** Running EnergyPlus MCP locally with ngrok tunnel

### Setup Requirements

1. EnergyPlus MCP HTTP server running locally on port 8081
2. ngrok tunnel active: `ngrok http 8081`
3. ngrok URL stored in Google Sheets (cell B1):
   - Sheet: `1XdLm6f9EY_AK6a6M4zH2Md4TzE3bSvTH-mXD6vL0KpE`

### Workflow Flow

```
Manual Trigger
    │
    ▼
Get ngrok URL (from Google Sheets)
    │
    ▼
Config (set parameters + API URL)
    │
    ▼
Health Check → [fail] → Stop: Server Unavailable
    │
    ▼
Fetch Weather (PVGIS) → [fail] → Stop: Weather Failed
    │
    ▼
Generate Model → [fail] → Stop: Model Failed
    │
    ▼
Run Simulation (120s timeout) → [fail] → Stop: Simulation Failed
    │
    ▼
Summary Results → Full Results → Export to Supabase → Done
```

---

## EnergyPlus GCP v1.0 (Production)

**Use when:** EnergyPlus MCP deployed on GCP VM

### Setup Requirements

1. EnergyPlus MCP container running on GCP VM
2. Port 8081 accessible (firewall rule configured)
3. VM external IP: `34.28.104.162`

### Key Differences from v0.1

| Aspect | v0.1 (Local) | v1.0 (GCP) |
|--------|--------------|------------|
| API URL source | Google Sheets (ngrok) | Hardcoded in Config |
| API Base URL | Dynamic | `http://34.28.104.162:8081` |
| ngrok dependency | Required | Not needed |
| Simulation timeout | 120s | 300s (for annual runs) |
| Weather timeout | Default | 60s (increased) |
| Final output | None | Summary JSON node |

### Workflow Flow

```
Manual Trigger
    │
    ▼
Config (hardcoded GCP VM URL + parameters)
    │
    ▼
Health Check → [fail] → Stop: Server Unavailable
    │
    ▼
Fetch Weather (PVGIS) → [fail] → Stop: Weather Failed
    │
    ▼
Generate Model → [fail] → Stop: Model Failed
    │
    ▼
Run Simulation (300s timeout) → [fail] → Stop: Simulation Failed
    │
    ▼
Summary Results → Full Results → Export to Supabase
    │
    ▼
Final Summary (JSON output)
```

---

## Configuration Parameters

Both workflows use similar configuration in the "Config" node:

```json
{
  "API_BASE_URL": "http://34.28.104.162:8081",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "location_name": "Cambridge_UK",
  "project_name": "Test Data Center",
  "building_type": "data_center",
  "data_center": {
    "rack_count": 25,
    "watts_per_rack": 2000
  },
  "simulation": {
    "annual": false,
    "design_day": true
  }
}
```

### Modifying Parameters

To change simulation settings:

1. Open the workflow in n8n
2. Click on the "Config" node
3. Modify the JSON in the "jsonOutput" field
4. Save and execute

---

## API Endpoints Used

| Endpoint | Method | Description | Timeout |
|----------|--------|-------------|---------|
| `/health` | GET | Server health check | 10s |
| `/api/weather/fetch` | POST | Download EPW from PVGIS | 60s |
| `/api/models/generate` | POST | Generate IDF from spec | 30s |
| `/api/simulation/run` | POST | Run EnergyPlus | 300s |
| `/api/simulation/results/summary` | GET | Summary results | default |
| `/api/simulation/results` | GET | Full results | default |
| `/api/export/supabase` | POST | Export to Supabase | default |

---

## Importing Workflows

1. Open n8n (http://34.28.104.162:5678 or local instance)
2. Click "Add Workflow" → "Import from File"
3. Select the appropriate JSON file
4. Click "Import"
5. Review and save the workflow

---

## Testing

### Test Health Check Only

```bash
# GCP VM
curl http://34.28.104.162:8081/health

# Local (with ngrok)
curl http://localhost:8081/health
```

### Test Full Workflow

1. Import the workflow into n8n
2. Click "Execute Workflow"
3. Monitor each step's output
4. Check Supabase for exported files

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Health check fails | Verify container is running: `docker ps \| grep energyplus` |
| Weather fetch timeout | PVGIS API may be slow; increase timeout or retry |
| Simulation fails | Check container logs: `docker logs energyplus-mcp` |
| Supabase export fails | Verify SUPABASE_URL and SUPABASE_KEY in container env |
| Connection refused | Check firewall rules for port 8081 |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1 | Jan 2025 | Initial local development version |
| v1.0 | Feb 2026 | GCP VM production version |
