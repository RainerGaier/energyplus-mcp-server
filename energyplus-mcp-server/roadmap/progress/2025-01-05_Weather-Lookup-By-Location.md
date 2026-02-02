# Progress Note: Weather Lookup by Location

**Date:** 2025-01-05
**Milestone:** 1 - Foundation
**Status:** Complete

---

## Summary

Implemented weather file lookup by latitude/longitude coordinates using the PVGIS API. The system can now automatically fetch TMY (Typical Meteorological Year) weather data for any location worldwide and save it as an EnergyPlus-compatible EPW file.

---

## Research Findings

### Weather Data Sources Evaluated

| Source | Coverage | API | Notes |
|--------|----------|-----|-------|
| Climate.OneBuilding.org | 16,100+ locations, 249 countries | No API | Manual download only, KML map access |
| PVGIS (EU JRC) | Worldwide | Yes, free | TMY data, outputs EPW directly |
| NREL NSRDB | Americas | Yes | Requires registration |
| Solcast | Worldwide | Yes | Commercial, requires API key |

**Selected: PVGIS** - Free API, no registration, worldwide coverage, direct EPW output.

### PVGIS API Details

- **Base URL:** `https://re.jrc.ec.europa.eu/api/v5_3/tmy`
- **Coverage Databases:**
  - PVGIS-SARAH3: Europe, Africa, Central Asia (high resolution)
  - PVGIS-NSRDB: Americas
  - PVGIS-ERA5: Worldwide (lower resolution fallback)
- **Rate Limit:** 30 calls/second per IP

---

## Implementation

### New Files Created

| File | Purpose |
|------|---------|
| `energyplus_mcp_server/utils/weather_lookup.py` | Weather lookup service class |
| `server.py` additions | 3 new MCP tools |

### MCP Tools Added

1. **`fetch_weather_by_location`** - Main tool to fetch and save weather files
   - Input: latitude, longitude, optional location_name
   - Output: EPW file path, metadata, location info

2. **`get_weather_coverage_info`** - Get coverage region information
   - Returns: Database descriptions and coverage areas

3. **`check_weather_coverage`** - Check coverage for specific location
   - Input: latitude, longitude
   - Output: Available databases, recommended database, quality notes

### EPW Compatibility Fixes

PVGIS EPW files required fixes for EnergyPlus compatibility:

1. **LOCATION line** - Replaced 'unknown' placeholders with proper values
2. **DATA PERIODS line** - Fixed date format to match EnergyPlus expectations
3. **Timezone** - Calculated from longitude when not provided

```python
# Example fix for LOCATION line:
# Before: LOCATION,unknown,-,unknown,ECMWF/ERA,unknown,52.205300,0.121800,0,21
# After:  LOCATION,Cambridge_UK,-,PVGIS,ECMWF/ERA,unknown,52.205300,0.121800,0,21
```

---

## Testing

### Test 1: Weather Fetch for Cambridge, UK (Cam and Ely Ouse catchment)

```
Location: 52.2053, 0.1218 (Cambridge, UK)
Coverage: PVGIS-SARAH3 (high-resolution satellite data)
Result: Success
File Size: 1,873,991 bytes
Elevation: 21.0m
```

### Test 2: Run Simulation with Fetched Weather

```
Model: 1ZoneDataCenterCRAC_wPumpedDXCoolingCoil.idf
Weather: Cambridge_UK_52.2053_0.1218.epw
Result: Success
Duration: 0:00:00.912780
```

---

## Usage Examples

### Fetch Weather for a Site Selection Location

```python
# When Rob's site selection identifies a location in the Cam and Ely Ouse catchment:
result = await fetch_weather_by_location(
    latitude=52.2053,
    longitude=0.1218,
    location_name="Cambridge_Manufacturing_Site"
)
# Returns EPW path that can be used in run_simulation()
```

### Check Coverage Before Fetching

```python
coverage = await check_weather_coverage(52.2053, 0.1218)
# Returns:
# {
#   "available_databases": ["PVGIS-SARAH3", "PVGIS-ERA5"],
#   "recommended_database": "PVGIS-SARAH3",
#   "notes": ["High-resolution satellite data available"]
# }
```

---

## Integration with Site Selection Workflow

This feature enables the following workflow from the project concept:

```
1. Site Selection (Rob) outputs: Location (lat/long)
    ↓
2. Technical Models (Rainer):
   a. fetch_weather_by_location(lat, lon, site_name)
   b. run_simulation(idf_model, weather_file=fetched_epw)
    ↓
3. Technical Reports for stakeholder review
```

---

## Roadmap Update

Updated `roadmap/phase1-approach.md`:

```markdown
| Capability              | Status      | Notes                                 |
| ----------------------- | ----------- | ------------------------------------- |
| Weather file handling   | ✅ Working  | PVGIS API integration, lat/long fetch |
```

### Milestone 1: Foundation
- [x] Fix cross-platform configuration (Windows + Linux/Docker)
- [x] Integrate weather file lookup by lat/long coordinates
- [ ] Design building specification input schema

---

## API Reference

### PVGIS Documentation
- User Manual: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en
- API Reference: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en

### Coverage Notes
- **UK locations** (Rob's catchment areas): Full PVGIS-SARAH3 coverage
- **South Africa** (Rainer's location): Full PVGIS-SARAH3 coverage
- **Remote locations**: ERA5 fallback available worldwide
