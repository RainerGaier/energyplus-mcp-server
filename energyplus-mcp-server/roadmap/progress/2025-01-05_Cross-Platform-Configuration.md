# Progress Note: Cross-Platform Configuration

**Date:** 2025-01-05

**Milestone:** 1 - Foundation

**Status:** Complete

---

## Summary

Implemented cross-platform configuration support so the MCP server works on both Windows and Linux/Docker without requiring manual environment variable setup.

---

## Problem

The original configuration had hardcoded Linux paths that failed on Windows:

| Location       | Hardcoded Value                                            | Issue                         |
| -------------- | ---------------------------------------------------------- | ----------------------------- |
| `config.py:34` | `workspace_root = "/workspace/energyplus-mcp-server"`      | Path doesn't exist on Windows |
| `config.py:36` | `temp_dir = "/tmp"`                                        | Linux-only temp path          |
| `config.py:37` | `output_dir = "/workspace/energyplus-mcp-server/outputs"`  | Path doesn't exist            |
| `config.py:91` | `default_installation = "/app/software/EnergyPlusV25-2-0"` | Docker-specific path          |
| `config.py:79` | `executable_path = .../energyplus`                         | Missing `.exe` on Windows     |

This meant Windows users had to manually set `EPLUS_IDD_PATH` and still encountered failures when the server tried to create log directories.

---

## Solution

### 1. Platform Detection

Added functions to detect the operating system and return appropriate defaults:

```python
def _is_windows() -> bool:
    return sys.platform == "win32"

def _get_platform_defaults() -> Dict[str, Any]:
    if _is_windows():
        # Windows: auto-discover EnergyPlus, use project root, Windows temp
        ...
    else:
        # Linux: use devcontainer defaults
        ...
```

### 2. Auto-Discovery of EnergyPlus (Windows)

The server now checks common installation locations:

- `C:/EnergyPlusV25-2-0`
- `C:/Program Files/EnergyPlusV25-2-0`
- `C:/Program Files (x86)/EnergyPlusV25-2-0`
- `~/EnergyPlusV25-2-0`

### 3. Project-Relative Paths

Instead of hardcoded absolute paths, workspace root now defaults to the project directory:

```python
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
```

### 4. Platform-Aware Executable

Windows gets `energyplus.exe`, Linux gets `energyplus`:

```python
"executable_name": "energyplus.exe" if _is_windows() else "energyplus"
```

### 5. Environment Variable Support

All paths can be overridden via environment variables:

| Variable                     | Purpose                           |
| ---------------------------- | --------------------------------- |
| `EPLUS_INSTALL_PATH`         | EnergyPlus installation directory |
| `EPLUS_IDD_PATH`             | Path to Energy+.idd file          |
| `EPLUS_WEATHER_PATH`         | Weather data directory            |
| `EPLUS_EXAMPLE_FILES_PATH`   | Example files directory           |
| `EPLUS_DEFAULT_WEATHER_FILE` | Default weather file              |
| `MCP_WORKSPACE_ROOT`         | Project workspace root            |
| `MCP_OUTPUT_DIR`             | Simulation outputs directory      |
| `MCP_TEMP_DIR`               | Temporary files directory         |
| `MCP_SAMPLE_FILES_PATH`      | Sample files directory            |

---

## Files Changed

| File                              | Change                                                    |
| --------------------------------- | --------------------------------------------------------- |
| `energyplus_mcp_server/config.py` | Added platform detection, auto-discovery, env var support |
| `.env.example`                    | New file documenting all environment variables            |
| `roadmap/phase1-approach.md`      | Updated status and setup instructions                     |

---

## Testing

### Test 1: Configuration Auto-Detection

```
Platform: win32
Project Root: C:\Users\gaierr\Energy_Projects\projects\EnergyPlus-MCP\energyplus-mcp-server

EnergyPlus Configuration:
- Installation Path: C:\EnergyPlusV25-2-0
- IDD Path: C:\EnergyPlusV25-2-0\Energy+.idd
- Executable Path: C:\EnergyPlusV25-2-0\energyplus.exe

Path Configuration:
- Workspace Root: C:\Users\gaierr\...\energyplus-mcp-server
- Output Dir: C:\Users\gaierr\...\energyplus-mcp-server\outputs
- Temp Dir: C:\Users\gaierr\AppData\Local\Temp

Path Validation:
- IDD exists: True
- Executable exists: True
- Weather dir exists: True
- Sample files exists: True
```

### Test 2: End-to-End Simulation

```
Model: 1ZoneDataCenterCRAC_wPumpedDXCoolingCoil.idf
Result: Success
Duration: 0:00:00.916435
Output: 19 files generated
```

---

## Backwards Compatibility

- Linux/Docker environments continue to work with existing defaults
- Existing `EPLUS_IDD_PATH` environment variable still works
- No breaking changes to the API

---

## Next Steps

Remaining Milestone 1 tasks:

- [ ] Design building specification input schema
- [ ] Integrate weather file lookup by lat/long coordinates