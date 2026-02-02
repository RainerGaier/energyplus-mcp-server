# EnergyPlus MCP Server - Architecture Design Document

**Version:** 1.0

**Last Updated:** February 2026

**Author:** Rainer Gaier

---

## 1. Overview

The EnergyPlus MCP Server is a Model Context Protocol (MCP) server that provides AI agents with comprehensive access to EnergyPlus building energy simulation capabilities. It is part of a larger **Stakeholder-Informed Rapid Site Selection & Technical Modelling Agentic System**.

### 1.1 Purpose

Enable AI agents to:

- Load, inspect, and modify EnergyPlus IDF building models
- Run energy simulations with customizable parameters
- Analyze HVAC systems and building performance
- Generate visualizations and reports
- Support iterative design workflows

### 1.2 System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agentic System Pipeline                              │
├─────────────────────────────────────────────────────────────────────────┤
│  1.0 Site Selection → 2.0 Stakeholder Prep → 3.0 Technical Models       │
│                                                     ↑                   │
│                                              EnergyPlus MCP ←──┐        │
│                                                     ↓          │        │
│  4.0 Stakeholder Feedback → 5.0 Design Adjustments → 6.0 Iteration      │
│                                                     ↓                   │
│                              7.0 Material Creation                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Claude Code │  │  n8n/HTTP   │  │ MCP Client  │  │   Custom    │     │
│  │   (stdio)   │  │  Workflows  │  │   (SSE)     │  │   Clients   │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
└─────────┼────────────────┼────────────────┼────────────────┼────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       TRANSPORT LAYER                                   │
│  ┌────────────────────────┐      ┌────────────────────────────────┐    │
│  │    MCP Server (stdio)   │      │    HTTP API Server (FastAPI)   │    │
│  │    Port: N/A            │      │    Port: 8081                  │    │
│  │    Protocol: MCP/JSON   │      │    Protocol: REST/JSON         │    │
│  └───────────┬─────────────┘      └──────────────┬─────────────────┘    │
└──────────────┼───────────────────────────────────┼──────────────────────┘
               │                                   │
               ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TOOLS LAYER                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     35+ MCP Tools                                  │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │  │
│  │  │   Model     │ │ Inspection  │ │Modification │ │ Simulation  │ │  │
│  │  │  Loading    │ │   Tools     │ │   Tools     │ │   Tools     │ │  │
│  │  │  (9 tools)  │ │  (9 tools)  │ │  (8 tools)  │ │  (4 tools)  │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │  │
│  │  │   Server    │ │  Weather    │ │  Template   │                 │  │
│  │  │ Management  │ │  Services   │ │  Services   │                 │  │
│  │  │  (5 tools)  │ │  (1 tool)   │ │  (3 tools)  │                 │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
               ▼                                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    EnergyPlusManager                             │    │
│  │  - IDF file loading and validation                               │    │
│  │  - Model inspection and modification                             │    │
│  │  - Simulation execution and monitoring                           │    │
│  │  - Results processing and export                                 │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │TemplateService│  │WeatherLookup │  │ DiagramGen   │  │ CloudStorage │ │
│  │              │  │              │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       INTEGRATION LAYER                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │     eppy        │  │    Graphviz     │  │    External APIs        │  │
│  │  (IDF parsing)  │  │  (Diagrams)     │  │  - PVGIS (weather)      │  │
│  │                 │  │                 │  │  - Supabase (storage)   │  │
│  │                 │  │                 │  │  - Google Drive         │  │
│  └────────┬────────┘  └─────────────────┘  └─────────────────────────┘  │
└───────────┼─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ENERGYPLUS ENGINE                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   EnergyPlus 25.2.0                              │    │
│  │  - energyplus executable                                         │    │
│  │  - Energy+.idd (data dictionary)                                 │    │
│  │  - Weather files (EPW format)                                    │    │
│  │  - Example/Reference files                                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Descriptions

| Component             | Description                                              | Technology         |
| --------------------- | -------------------------------------------------------- | ------------------ |
| **MCP Server**        | Model Context Protocol server for AI agent communication | FastMCP, Python    |
| **HTTP API**          | RESTful API for n8n and external integrations            | FastAPI, Uvicorn   |
| **EnergyPlusManager** | Central orchestration for EnergyPlus operations          | Python, eppy       |
| **TemplateService**   | Building template management and model generation        | Python, JSON       |
| **WeatherLookup**     | Weather file retrieval via PVGIS API                     | Python, httpx      |
| **DiagramGenerator**  | HVAC system visualization                                | Graphviz, NetworkX |
| **CloudStorage**      | Integration with cloud storage services                  | Supabase, GCS      |

---

## 3. Data Flow

### 3.1 Simulation Workflow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Input    │────▶│   Model    │────▶│ Simulation │────▶│   Output   │
│            │     │ Generation │     │            │     │            │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│• Location  │     │• Template  │     │• EnergyPlus│     │• CSV data  │
│  (lat/lng) │     │  Selection │     │  execution │     │• HTML      │
│• Building  │     │• Parameter │     │• Weather   │     │  reports   │
│  spec      │     │  injection │     │  file      │     │• SQLite    │
│• Config    │     │• IDF gen   │     │• Timeout   │     │• Diagrams  │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

### 3.2 File Storage Structure

```
/workspace/energyplus-mcp-server/
├── outputs/                      # Simulation outputs
│   ├── models/                   # Generated IDF models
│   ├── weather_files/            # Downloaded EPW files
│   └── YYYYMMDD_HHMMSS_<name>/   # Timestamped simulation results
│       ├── eplusout.csv          # Time-series data
│       ├── eplustbl.htm          # Tabular reports
│       ├── eplusout.sql          # SQLite database
│       └── ...
├── sample_files/                 # Reference IDF files
├── templates/                    # Building templates (JSON + IDF)
│   ├── data_center/
│   └── manufacturing/
├── logs/                         # Application logs
└── schemas/                      # JSON schemas
```

---

## 4. Tool Categories

### 4.1 Model Configuration & Loading (9 tools)

| Tool                        | Description                                   |
| --------------------------- | --------------------------------------------- |
| `load_idf_model`            | Load and parse IDF files                      |
| `validate_idf`              | Comprehensive model validation                |
| `list_available_files`      | Browse sample and weather files               |
| `copy_file`                 | Intelligent file copying with path resolution |
| `get_model_summary`         | Extract model metadata                        |
| `check_simulation_settings` | Review simulation control                     |
| `modify_simulation_control` | Modify simulation parameters                  |
| `modify_run_period`         | Adjust simulation time periods                |
| `get_server_configuration`  | Get server config info                        |

### 4.2 Model Inspection (9 tools)

| Tool                         | Description                   |
| ---------------------------- | ----------------------------- |
| `list_zones`                 | List thermal zones            |
| `get_surfaces`               | Get building surfaces         |
| `get_materials`              | Extract material definitions  |
| `inspect_schedules`          | Analyze schedules             |
| `inspect_people`             | Analyze occupancy             |
| `inspect_lights`             | Analyze lighting loads        |
| `inspect_electric_equipment` | Analyze equipment loads       |
| `get_output_variables`       | Get/discover output variables |
| `get_output_meters`          | Get/discover energy meters    |

### 4.3 Model Modification (8 tools)

| Tool                          | Description               |
| ----------------------------- | ------------------------- |
| `modify_people`               | Update occupancy settings |
| `modify_lights`               | Update lighting loads     |
| `modify_electric_equipment`   | Update equipment loads    |
| `change_infiltration_by_mult` | Modify infiltration rates |
| `add_window_film_outside`     | Add window films          |
| `add_coating_outside`         | Apply surface coatings    |
| `add_output_variables`        | Add output variables      |
| `add_output_meters`           | Add energy meters         |

### 4.4 Simulation & HVAC (4 tools)

| Tool                        | Description                  |
| --------------------------- | ---------------------------- |
| `run_energyplus_simulation` | Execute simulations          |
| `create_interactive_plot`   | Generate HTML visualizations |
| `discover_hvac_loops`       | Find HVAC loops              |
| `get_loop_topology`         | Get loop details             |

### 4.5 Server Management (5 tools)

| Tool                     | Description            |
| ------------------------ | ---------------------- |
| `visualize_loop_diagram` | Generate HVAC diagrams |
| `get_server_status`      | Check health           |
| `get_server_logs`        | View logs              |
| `get_error_logs`         | Get error logs         |
| `clear_logs`             | Clear/rotate logs      |

### 4.6 External Services (4 tools)

| Tool                        | Description              |
| --------------------------- | ------------------------ |
| `fetch_weather_by_location` | Download EPW via PVGIS   |
| `list_building_templates`   | List available templates |
| `get_template_details`      | Get template metadata    |
| `generate_building_model`   | Generate IDF from spec   |

---

## 5. Deployment Architecture

### 5.1 Development Environment (DevContainer)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     VS Code DevContainer                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Base: python:3.12-slim                                        │  │
│  │  EnergyPlus: 25.2.0 (auto-detect arm64/amd64)                 │  │
│  │  Tools: uv, Node.js 20, Graphviz, X11 libs                    │  │
│  │  User: vscode (non-root)                                       │  │
│  │                                                                │  │
│  │  Ports:                                                        │  │
│  │    6274 → MCP Inspector                                        │  │
│  │    8080 → HTTP Server                                          │  │
│  │    3000 → Development Server                                   │  │
│  │                                                                │  │
│  │  Mount: ${localWorkspaceFolder} → /workspace/energyplus-mcp    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Production Environment (GCP VM)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GCP VM (qsdsan-vm)                               │
│                     34.28.104.162                                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Docker Network: qsdsan-network              │  │
│  │                                                                │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │  │
│  │  │  QSDsan Engine  │  │ EnergyPlus MCP  │  │   Gotenberg   │  │  │
│  │  │    Port 8080    │  │    Port 8081    │  │   Port 3000   │  │  │
│  │  │                 │  │                 │  │   (shared)    │  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────┘  │  │
│  │                                                                │  │
│  │  ┌─────────────────┐  ┌─────────────────────────────────────┐  │  │
│  │  │      n8n        │  │         Shared Volumes              │  │  │
│  │  │   Port 5678     │  │  - energyplus_jobs:/app/jobs        │  │  │
│  │  │   (workflows)   │  │  - qsdsan_jobs:/app/jobs            │  │  │
│  │  └─────────────────┘  └─────────────────────────────────────┘  │  │
│  │                                                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Configuration Management

### 6.1 Environment Variables

| Variable             | Purpose                 | Default (Windows)      | Default (Docker)                              |
| -------------------- | ----------------------- | ---------------------- | --------------------------------------------- |
| `EPLUS_INSTALL_PATH` | EnergyPlus installation | `C:/EnergyPlusV25-2-0` | `/app/software/EnergyPlusV25-2-0`             |
| `EPLUS_IDD_PATH`     | Energy+.idd location    | Auto-derived           | `/app/software/EnergyPlusV25-2-0/Energy+.idd` |
| `MCP_WORKSPACE_ROOT` | Project root            | Auto-detected          | `/workspace/energyplus-mcp-server`            |
| `MCP_OUTPUT_DIR`     | Output directory        | `./outputs`            | `/workspace/.../outputs`                      |
| `MCP_TEMP_DIR`       | Temp directory          | `C:/Temp`              | `/tmp`                                        |
| `ENERGYPLUS_PORT`    | HTTP server port        | N/A                    | `8081`                                        |
| `OPENAI_API_KEY`     | AI analysis (optional)  | N/A                    | From `.env`                                   |

### 6.2 Platform Detection

The configuration system auto-detects the platform and applies appropriate defaults:

```python
def _is_windows() -> bool:
    return sys.platform == "win32"

def _get_platform_defaults() -> Dict[str, Any]:
    if _is_windows():
        return {"energyplus_install": "C:/EnergyPlusV25-2-0", ...}
    else:
        return {"energyplus_install": "/app/software/EnergyPlusV25-2-0", ...}
```

---

## 7. Security Considerations

### 7.1 Container Security

- Non-root user (`vscode`) in DevContainer
- Minimal base image (`python:3.12-slim`)
- No unnecessary system services
- Read-only mounts where possible

### 7.2 API Security

- Health check endpoints for monitoring
- CORS configuration for HTTP API
- No authentication by default (add for production)
- Firewall rules required for external access

### 7.3 Data Security

- Simulation files stored locally by default
- Optional cloud storage (Supabase/GCS) for persistence
- Environment variables for sensitive configuration
- `.env` files excluded from version control

---

## 8. Monitoring and Logging

### 8.1 Log Configuration

```
logs/
├── energyplus_mcp_server.log    # All logs (rotating, 10MB/5 backups)
└── energyplus_mcp_errors.log    # Error logs only (rotating, 5MB/3 backups)
```

### 8.2 Health Checks

- `/health` endpoint on HTTP server
- Docker health check configured (30s interval)
- Startup validation of EnergyPlus installation

---

## 9. Dependencies

### 9.1 Core Dependencies

| Package             | Version | Purpose                    |
| ------------------- | ------- | -------------------------- |
| `mcp[cli]`          | Latest  | Model Context Protocol     |
| `fastapi`           | Latest  | HTTP API framework         |
| `uvicorn[standard]` | Latest  | ASGI server                |
| `eppy`              | Latest  | IDF file manipulation      |
| `pandas`            | Latest  | Data processing            |
| `plotly`            | Latest  | Interactive visualizations |
| `graphviz`          | Latest  | Diagram generation         |
| `networkx`          | Latest  | Graph operations           |
| `pydantic>=2.0`     | 2.x     | Data validation            |

### 9.2 Optional Dependencies

| Package                    | Purpose                  |
| -------------------------- | ------------------------ |
| `google-api-python-client` | Google Drive integration |
| `supabase`                 | Supabase storage         |
| `geomeppy`                 | 3D geometry extraction   |
| `trimesh`                  | OBJ/glTF conversion      |

---

## 10. Future Considerations

### 10.1 Scalability

- Horizontal scaling via multiple containers
- Queue-based simulation execution for long runs
- Caching layer for weather data and templates

### 10.2 Integration

- OpenStudio SDK integration for advanced HVAC
- Real-time simulation progress streaming
- WebSocket support for live updates

### 10.3 Features

- Additional building templates (office, retail, residential)
- Advanced reporting with PDF generation
- Cost analysis and utility rate integration