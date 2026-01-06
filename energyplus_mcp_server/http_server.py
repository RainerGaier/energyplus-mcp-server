"""
EnergyPlus MCP Server - HTTP API Wrapper

Provides REST API endpoints for n8n workflow integration.
This wraps the MCP tools as HTTP endpoints using FastAPI.

Usage:
    # Run the server
    python -m energyplus_mcp_server.http_server

    # Or with uvicorn
    uvicorn energyplus_mcp_server.http_server:app --host 0.0.0.0 --port 8000
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import our existing components
from energyplus_mcp_server.energyplus_tools import EnergyPlusManager
from energyplus_mcp_server.config import get_config
from energyplus_mcp_server.utils.weather_lookup import WeatherLookup, WeatherLookupError
from energyplus_mcp_server.utils.template_service import TemplateService, TemplateServiceError

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize configuration
config = get_config()

# Initialize FastAPI app
app = FastAPI(
    title="EnergyPlus HTTP API",
    description="REST API for EnergyPlus building energy simulation - designed for n8n workflow integration",
    version=config.server.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for n8n access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for n8n
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (reuse from MCP server)
ep_manager = EnergyPlusManager(config)
template_service = TemplateService()
weather_lookup = WeatherLookup(
    output_dir=os.path.join(config.paths.output_dir, "weather_files")
)


# =============================================================================
# Pydantic Models for Request/Response Validation
# =============================================================================

class LocationModel(BaseModel):
    """Location specification"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    site_name: Optional[str] = Field(None, description="Location name for identification")
    elevation_m: Optional[float] = Field(None, description="Site elevation in meters")
    catchment_area: Optional[str] = Field(None, description="Catchment area identifier")


class GeometryModel(BaseModel):
    """Building geometry specification"""
    floor_area_m2: Optional[float] = Field(None, ge=50, le=100000, description="Total floor area in m²")
    length_m: Optional[float] = Field(None, ge=5, le=500, description="Building length in meters")
    width_m: Optional[float] = Field(None, ge=5, le=500, description="Building width in meters")
    height_m: Optional[float] = Field(None, ge=2.5, le=50, description="Building height in meters")
    num_floors: Optional[int] = Field(None, ge=1, le=50, description="Number of floors")
    orientation_deg: Optional[float] = Field(None, ge=0, le=360, description="Building rotation from north")


class DataCenterSpecModel(BaseModel):
    """Data center specific parameters"""
    it_load_kw: Optional[float] = Field(None, ge=1, le=100000, description="Total IT load in kW")
    target_pue: Optional[float] = Field(None, ge=1.0, le=3.0, description="Target PUE")
    tier_level: Optional[int] = Field(None, ge=1, le=4, description="Uptime tier classification")
    cooling_type: Optional[str] = Field(None, description="Primary cooling approach")
    rack_count: Optional[int] = Field(None, ge=1, le=10000, description="Number of server racks")
    watts_per_rack: Optional[float] = Field(None, ge=100, le=50000, description="Average power per rack")


class ManufacturingSpecModel(BaseModel):
    """Manufacturing facility specific parameters"""
    process_type: Optional[str] = Field(None, description="Type of manufacturing process")
    process_load_kw: Optional[float] = Field(None, ge=0, le=100000, description="Process equipment load in kW")
    process_heat_kw: Optional[float] = Field(None, ge=0, le=100000, description="Process heat generation in kW")
    process_heat_fraction: Optional[float] = Field(None, ge=0, le=1.0, description="Fraction as radiant heat")
    ventilation_ach: Optional[float] = Field(None, ge=0.5, le=50, description="Required air changes per hour")
    occupancy_count: Optional[int] = Field(None, ge=0, le=10000, description="Number of occupants")


class SetpointsModel(BaseModel):
    """Temperature setpoints"""
    cooling_setpoint_c: Optional[float] = Field(None, ge=15, le=35, description="Cooling setpoint in °C")
    heating_setpoint_c: Optional[float] = Field(None, ge=10, le=25, description="Heating setpoint in °C")


class SimulationOptionsModel(BaseModel):
    """Simulation configuration"""
    run_annual: bool = Field(False, description="Run full annual simulation")
    run_design_days: bool = Field(True, description="Run design day simulations")
    sizing_run: bool = Field(False, description="Perform HVAC sizing calculations")
    detailed_outputs: bool = Field(False, description="Generate detailed hourly outputs")


class BuildingSpecRequest(BaseModel):
    """Complete building specification for model generation"""
    project_id: Optional[str] = Field(None, description="Unique project identifier")
    project_name: Optional[str] = Field(None, description="Human-readable project name")
    location: LocationModel
    building_type: str = Field(..., description="Building type: data_center, manufacturing, warehouse, office")
    geometry: Optional[GeometryModel] = None
    data_center: Optional[DataCenterSpecModel] = None
    manufacturing: Optional[ManufacturingSpecModel] = None
    setpoints: Optional[SetpointsModel] = None
    simulation_options: Optional[SimulationOptionsModel] = None
    template_id: Optional[str] = Field(None, description="Specific template to use")
    output_filename: Optional[str] = Field(None, description="Output IDF filename")


class WeatherFetchRequest(BaseModel):
    """Request for weather file fetch"""
    latitude: float = Field(..., ge=-90, le=90, description="Site latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Site longitude")
    location_name: Optional[str] = Field(None, description="Location name for file naming")


class SimulationRunRequest(BaseModel):
    """Request to run EnergyPlus simulation"""
    idf_path: str = Field(..., description="Path to IDF file")
    weather_file: Optional[str] = Field(None, description="Path to EPW weather file")
    output_directory: Optional[str] = Field(None, description="Output directory for results")
    annual: bool = Field(True, description="Run annual simulation")
    design_day: bool = Field(False, description="Run design day only")
    readvars: bool = Field(True, description="Process outputs with ReadVarsESO")
    expandobjects: bool = Field(True, description="Expand HVAC templates")


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """API root - returns server info"""
    return {
        "name": "EnergyPlus HTTP API",
        "version": config.server.version,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "weather": "/api/weather",
            "templates": "/api/templates",
            "models": "/api/models",
            "simulation": "/api/simulation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "energyplus_version": config.energyplus.version,
        "server_version": config.server.version
    }


# =============================================================================
# Weather Endpoints
# =============================================================================

@app.post("/api/weather/fetch")
async def fetch_weather(request: WeatherFetchRequest):
    """
    Fetch weather data for a location.

    Downloads TMY weather data from PVGIS API and saves as EPW file.
    """
    try:
        result = weather_lookup.fetch_weather_by_location(
            latitude=request.latitude,
            longitude=request.longitude,
            location_name=request.location_name
        )
        return result
    except WeatherLookupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Weather fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/coverage")
async def get_weather_coverage():
    """Get information about weather data coverage regions"""
    try:
        coverage = weather_lookup.get_coverage_info()
        return {
            "success": True,
            "coverage_regions": coverage,
            "api_source": "PVGIS v5.3 (European Commission)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/check-coverage")
async def check_weather_coverage(latitude: float, longitude: float):
    """Check weather data availability for a specific location"""
    try:
        coverage = weather_lookup.check_location_coverage(latitude, longitude)
        return {"success": True, **coverage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Template Endpoints
# =============================================================================

@app.get("/api/templates")
async def list_templates(building_type: Optional[str] = None):
    """
    List available building templates.

    Optionally filter by building type (data_center, manufacturing, etc.)
    """
    try:
        templates = template_service.list_templates(building_type)
        return {
            "success": True,
            "count": len(templates),
            "templates": templates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_id}")
async def get_template_details(template_id: str):
    """Get detailed information about a specific template"""
    try:
        template = template_service.get_template(template_id)

        with open(template.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return {
            "success": True,
            "template_id": template_id,
            "metadata": metadata
        }
    except TemplateServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schemas/building-specification")
async def get_building_schema():
    """Get the JSON schema for building specifications"""
    try:
        schema_path = Path(__file__).parent.parent / "schemas" / "building_specification.json"

        if not schema_path.exists():
            raise HTTPException(status_code=404, detail="Schema not found")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        return {"success": True, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Model Generation Endpoints
# =============================================================================

@app.post("/api/models/generate")
async def generate_building_model(request: BuildingSpecRequest):
    """
    Generate a customized EnergyPlus IDF model from building specification.

    This is the main entry point for creating simulation-ready models.
    """
    try:
        # Convert Pydantic model to dict
        building_spec = request.model_dump(exclude_none=True, exclude={"template_id", "output_filename"})

        # Handle location conversion
        if "location" in building_spec:
            building_spec["location"] = dict(building_spec["location"])

        # Generate output filename if not provided
        output_filename = request.output_filename
        if not output_filename:
            project_name = request.project_name or "model"
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{safe_name}_{timestamp}.idf"

        # Determine output path
        output_path = os.path.join(config.paths.output_dir, "models", output_filename)

        # Generate the model
        result = template_service.generate_model(
            building_spec=building_spec,
            output_path=output_path,
            template_id=request.template_id
        )

        return result

    except TemplateServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Model generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Simulation Endpoints
# =============================================================================

@app.post("/api/simulation/run")
async def run_simulation(request: SimulationRunRequest):
    """
    Run EnergyPlus simulation with specified IDF and weather file.

    Returns simulation results including output file paths.
    """
    try:
        result = ep_manager.run_simulation(
            idf_path=request.idf_path,
            weather_file=request.weather_file,
            output_directory=request.output_directory,
            annual=request.annual,
            design_day=request.design_day,
            readvars=request.readvars,
            expandobjects=request.expandobjects
        )
        return json.loads(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/status")
async def get_simulation_status():
    """Get current simulation status and server health"""
    return {
        "status": "ready",
        "energyplus_available": os.path.exists(config.energyplus.executable_path) if config.energyplus.executable_path else False,
        "energyplus_version": config.energyplus.version,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/simulation/results")
async def get_simulation_results(output_directory: str, include_timeseries: bool = False):
    """
    Get simulation results from an output directory.

    Returns summary data from the HTML tables and optionally time-series CSV data.

    Args:
        output_directory: Path to the simulation output directory
        include_timeseries: If True, includes parsed CSV time-series data (can be large)
    """
    try:
        output_path = Path(output_directory)

        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"Output directory not found: {output_directory}")

        results = {
            "success": True,
            "output_directory": output_directory,
            "files": {},
            "summary": {},
            "errors": [],
            "warnings": []
        }

        # List all output files
        for f in output_path.iterdir():
            if f.is_file():
                results["files"][f.suffix.lower()] = results["files"].get(f.suffix.lower(), []) + [f.name]

        # Parse error file for warnings/errors
        err_file = output_path / "eplusout.err"
        if err_file.exists():
            with open(err_file, "r", encoding="utf-8", errors="ignore") as f:
                err_content = f.read()
                for line in err_content.split("\n"):
                    if "** Warning **" in line:
                        results["warnings"].append(line.strip())
                    elif "** Severe **" in line or "** Fatal **" in line:
                        results["errors"].append(line.strip())

        # Parse end file for summary
        end_file = output_path / "eplusout.end"
        if end_file.exists():
            with open(end_file, "r", encoding="utf-8", errors="ignore") as f:
                end_content = f.read()
                results["summary"]["completion_status"] = end_content.strip()

        # Parse CSV meter data if available
        meter_csv = None
        for f in output_path.glob("*Meter.csv"):
            meter_csv = f
            break

        if meter_csv and meter_csv.exists():
            import pandas as pd
            try:
                df = pd.read_csv(meter_csv)
                # Get column names (these are the meter names)
                results["summary"]["meters"] = list(df.columns[1:])  # Skip Date/Time column

                # Calculate totals for energy meters
                energy_totals = {}
                for col in df.columns[1:]:
                    if "Electricity" in col or "Gas" in col or "Energy" in col:
                        total = df[col].sum()
                        energy_totals[col] = {
                            "total": float(total),
                            "unit": "J"
                        }
                results["summary"]["energy_totals"] = energy_totals

                if include_timeseries:
                    # Convert to list of dicts for JSON
                    results["timeseries"] = {
                        "meter_data": df.to_dict(orient="records")
                    }
            except Exception as e:
                results["warnings"].append(f"Could not parse meter CSV: {str(e)}")

        # Parse table output for key metrics
        tbl_file = output_path / "eplustbl.htm"
        if tbl_file.exists():
            results["summary"]["html_report_available"] = True
            # Extract key values from HTML (simplified parsing)
            try:
                with open(tbl_file, "r", encoding="utf-8", errors="ignore") as f:
                    html_content = f.read()
                    # Look for common summary values
                    if "Total Site Energy" in html_content:
                        results["summary"]["has_energy_summary"] = True
            except Exception:
                pass

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting simulation results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/results/summary")
async def get_results_summary(output_directory: str):
    """
    Get a condensed summary of simulation results suitable for reporting.

    Returns key energy metrics, PUE (for data centers), and any errors/warnings.
    """
    try:
        output_path = Path(output_directory)

        if not output_path.exists():
            raise HTTPException(status_code=404, detail=f"Output directory not found: {output_directory}")

        summary = {
            "success": True,
            "output_directory": output_directory,
            "simulation_completed": False,
            "energy_summary": {},
            "warnings_count": 0,
            "errors_count": 0,
            "key_metrics": {}
        }

        # Check completion
        end_file = output_path / "eplusout.end"
        if end_file.exists():
            with open(end_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                summary["simulation_completed"] = "Successfully" in content

        # Count warnings/errors
        err_file = output_path / "eplusout.err"
        if err_file.exists():
            with open(err_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                summary["warnings_count"] = content.count("** Warning **")
                summary["errors_count"] = content.count("** Severe **") + content.count("** Fatal **")

        # Parse meter data for energy summary
        for meter_csv in output_path.glob("*Meter.csv"):
            import pandas as pd
            try:
                df = pd.read_csv(meter_csv)

                for col in df.columns[1:]:
                    total_j = df[col].sum()
                    # Convert to more useful units
                    total_kwh = total_j / 3600000  # J to kWh
                    total_gj = total_j / 1e9  # J to GJ

                    summary["energy_summary"][col] = {
                        "total_J": float(total_j),
                        "total_kWh": float(total_kwh),
                        "total_GJ": float(total_gj)
                    }

                # Calculate PUE if we have IT and Facility electricity
                facility_elec = None
                it_elec = None
                for col in df.columns:
                    if "Electricity:Facility" in col:
                        facility_elec = df[col].sum()
                    if "ITE" in col or "IT Equipment" in col:
                        it_elec = df[col].sum()

                if facility_elec and it_elec and it_elec > 0:
                    summary["key_metrics"]["PUE"] = float(facility_elec / it_elec)

            except Exception as e:
                summary["parse_error"] = str(e)
            break

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting results summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/read")
async def read_output_file(file_path: str, max_lines: int = 1000):
    """
    Read contents of an output file.

    Args:
        file_path: Full path to the file to read
        max_lines: Maximum number of lines to return (default 1000)
    """
    try:
        path = Path(file_path)

        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Security: only allow reading from outputs directory
        outputs_dir = Path(config.paths.output_dir).resolve()
        if not str(path.resolve()).startswith(str(outputs_dir)):
            raise HTTPException(status_code=403, detail="Access denied: can only read files from outputs directory")

        # Read file
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        total_lines = len(lines)
        truncated = total_lines > max_lines

        return {
            "success": True,
            "file_path": file_path,
            "file_name": path.name,
            "total_lines": total_lines,
            "truncated": truncated,
            "content": "".join(lines[:max_lines])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Model Inspection Endpoints
# =============================================================================

@app.get("/api/models/info")
async def get_model_info(idf_path: str):
    """Get basic information about an IDF model"""
    try:
        result = ep_manager.load_idf(idf_path)
        return {"success": True, "model_info": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/zones")
async def list_model_zones(idf_path: str):
    """List all zones in an IDF model"""
    try:
        result = ep_manager.list_zones(idf_path)
        return json.loads(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/validate")
async def validate_model(idf_path: str):
    """Validate an IDF model"""
    try:
        result = ep_manager.validate_idf(idf_path)
        return json.loads(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# File Listing Endpoints
# =============================================================================

@app.get("/api/files/available")
async def list_available_files(
    include_example_files: bool = False,
    include_weather_data: bool = False
):
    """List available sample files, examples, and weather data"""
    try:
        result = ep_manager.list_available_files(include_example_files, include_weather_data)
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting EnergyPlus HTTP API v{config.server.version}")
    logger.info(f"EnergyPlus version: {config.energyplus.version}")
    logger.info("API docs available at http://localhost:8000/docs")

    uvicorn.run(
        "energyplus_mcp_server.http_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
