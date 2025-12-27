# EnergyPlus MCP Server

A Model Context Protocol (MCP) server for EnergyPlus building energy simulation. This server enables AI assistants like Claude to interact with EnergyPlus models, run simulations, analyze results, and generate visualizations.

## Features

- **Model Inspection**: Load, validate, and inspect IDF files
- **Simulation Execution**: Run EnergyPlus simulations with weather files
- **HVAC Analysis**: Discover loops, inspect topology, generate diagrams
- **Output Management**: Configure output variables and meters
- **Visualization**: Create interactive Plotly charts from simulation results
- **Model Modification**: Modify simulation controls, run periods, internal loads, and more

## Requirements

- Docker and Docker Compose
- EnergyPlus 25.2 (included in Docker image)
- Python 3.12+ (for local development)

## Quick Start

### Using Docker (Recommended)

1. Build and start the container:
   ```bash
   docker-compose up -d
   ```

2. Configure your MCP client (e.g., Claude Code) to connect to the server.

### Local Development

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Set EnergyPlus paths and run:
   ```bash
   export ENERGYPLUS_PATH=/path/to/EnergyPlusV25-2-0
   python -m energyplus_mcp_server.server
   ```

## Project Structure

```
energyplus-mcp-server/
├── energyplus_mcp_server/    # MCP server source code
│   ├── server.py             # Main MCP server
│   ├── energyplus_tools.py   # EnergyPlus tool implementations
│   └── utils/                # Utility modules
│       ├── diagrams.py       # HVAC diagram generation
│       ├── path_utils.py     # File path resolution
│       ├── output_variables.py
│       ├── output_meters.py
│       └── ...
├── sample_files/             # Sample IDF and weather files
├── tests/                    # Test suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Sample Files

The `sample_files/` directory contains EnergyPlus models updated for version 25.2:

| File | Description |
|------|-------------|
| `1ZoneUncontrolled.idf` | Simple single-zone model |
| `1ZoneEvapCooler.idf` | Single zone with evaporative cooling |
| `1ZoneDataCenterCRAC_wApproachTemp.idf` | Data center with CRAC unit |
| `5ZoneAirCooled.idf` | Multi-zone VAV system |
| `LgOffVAV.idf` | Large office VAV system |
| `USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw` | San Francisco weather file |

## Available Tools

### Model Operations
- `load_idf_model` - Load and validate IDF files
- `get_model_summary` - Get building and simulation info
- `validate_idf` - Validate model structure
- `list_zones` - List all thermal zones
- `get_surfaces` - Get surface geometry
- `get_materials` - Get material properties

### Simulation
- `run_energyplus_simulation` - Execute simulations
- `check_simulation_settings` - Review SimulationControl
- `modify_simulation_control` - Update simulation settings
- `modify_run_period` - Change run period dates

### HVAC
- `discover_hvac_loops` - Find all HVAC loops
- `get_loop_topology` - Get detailed loop structure
- `visualize_loop_diagram` - Generate HVAC diagrams

### Outputs
- `get_output_variables` - List/discover output variables
- `get_output_meters` - List/discover output meters
- `add_output_variables` - Add variables to model
- `add_output_meters` - Add meters to model
- `create_interactive_plot` - Generate Plotly visualizations

### Internal Loads
- `inspect_people` / `modify_people`
- `inspect_lights` / `modify_lights`
- `inspect_electric_equipment` / `modify_electric_equipment`
- `inspect_schedules`

### Envelope
- `add_window_film_outside` - Apply window films
- `add_coating_outside` - Apply exterior coatings
- `change_infiltration_by_mult` - Modify infiltration rates

## Configuration

The server can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENERGYPLUS_PATH` | Path to EnergyPlus installation | `/app/software/EnergyPlusV25-2-0` |
| `WORKSPACE_ROOT` | Working directory | `/workspace/energyplus-mcp-server` |
| `DEBUG` | Enable debug logging | `false` |

## Version History

- **v0.1.0** - Initial release with EnergyPlus 25.2 support
  - Sample files transitioned from 25.1 to 25.2
  - Fixed RunPeriod configurations for annual simulations

## License

MIT License

## Acknowledgments

- [EnergyPlus](https://energyplus.net/) - Building energy simulation engine by NREL/DOE
- [eppy](https://github.com/santoshphilip/eppy) - Python library for EnergyPlus IDF files
- [Model Context Protocol](https://modelcontextprotocol.io/) - Protocol for AI tool integration
