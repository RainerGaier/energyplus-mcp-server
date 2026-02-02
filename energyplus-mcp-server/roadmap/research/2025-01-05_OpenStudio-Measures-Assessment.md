# Research Note: OpenStudio Measures Assessment

**Date:** 2025-01-05

**Topic:** Using OpenStudio Measures for Building Templates

**Status:** Research Complete

---

## Summary

OpenStudio Measures and the Building Component Library (BCL) offer a potential source for standardized building templates with pre-configured HVAC systems. This note evaluates the feasibility and approach for leveraging these resources in the EnergyPlus MCP Server.

---

## What are OpenStudio Measures?

Measures are Ruby scripts that:
1. **ModelMeasures (M)**: Modify OpenStudio models (add/remove/change objects)
2. **EnergyPlusMeasures (E)**: Modify IDF files directly
3. **ReportingMeasures (R)**: Generate custom reports from simulation results
4. **UtilityMeasures (U)**: Perform utility functions

Measures can be chained together in workflows to:
- Create prototype buildings from scratch
- Add/modify HVAC systems
- Apply energy efficiency measures
- Generate compliance reports

---

## Building Component Library (BCL)

**URL:** https://bcl.nrel.gov/

### Available Resources

| Type | Count | Description |
|------|-------|-------------|
| Measures | 210+ | Ruby scripts for model modification |
| Components | 500+ | HVAC equipment, constructions, schedules |
| Prototype Buildings | 16+ | DOE Commercial Reference Buildings |

### Relevant Measures for Project

#### Prototype Building Creation
- `create_DOE_prototype_building` - Creates complete building models
- `create_typical_DOE_building_from_model` - Parametric prototype generation
- Supports 16 US climate zones + international locations

#### HVAC Systems
- `Add Data Center Single Duct CRAC System`
- `Add VRF Heat Pump System`
- `Add Chilled Water System`
- `Add Central Air Source Heat Pump`
- `Add Packaged Rooftop Heat Pump`
- `Replace HVAC with Ground Source Heat Pump`

#### Building Types Available
1. LargeOffice
2. MediumOffice
3. SmallOffice
4. Warehouse (non-refrigerated)
5. RetailStandalone
6. RetailStripmall
7. PrimarySchool
8. SecondarySchool
9. Hospital
10. Outpatient
11. LargeHotel
12. SmallHotel
13. MidriseApartment
14. HighriseApartment
15. QuickServiceRestaurant
16. FullServiceRestaurant

---

## Gap Analysis

### Available Now
✅ Office buildings (small/medium/large)
✅ Warehouses (adaptable for light manufacturing)
✅ Data center HVAC components
✅ Heat pump systems (air-source, ground-source, VRF)
✅ Standard climate zone templates

### Gaps for Project
❌ Explicit manufacturing facility prototype
❌ UK/Europe-specific building standards (primarily US-focused)
❌ Industrial process loads (manufacturing equipment)
❌ Custom data center layouts (only HVAC components available)

---

## Integration Options

### Option A: Full OpenStudio Integration

```
MCP Server
    ├── OpenStudio SDK (Ruby)
    │   ├── Measure Runner
    │   └── OSW Workflow Engine
    ├── EnergyPlus
    └── Python MCP Tools
```

**Pros:**
- Full parametric control via measures
- Access to entire BCL library
- Community-maintained templates

**Cons:**
- Adds Ruby dependency
- More complex Docker image
- Two model formats (OSM + IDF)

### Option B: IDF Template Extraction

```
One-time: Use OpenStudio to generate IDF templates
    ↓
Store IDFs in MCP Server /templates folder
    ↓
Python tools modify IDF parameters directly
```

**Pros:**
- Simple deployment (EnergyPlus only)
- Fast modifications via Python
- No Ruby dependency

**Cons:**
- Lose measure flexibility
- Manual template updates
- Limited parametric range

### Option C: Hybrid Approach (Recommended)

```
Phase 1 (Now):
    - Extract IDF templates from key measures
    - Store as seed models in /templates
    - Python parametric tools for basic modifications

Phase 2 (Later):
    - Add OpenStudio integration for complex scenarios
    - Use measures for major building type changes
    - Keep IDF path for quick iterations
```

**Pros:**
- Start simple, scale as needed
- Immediate progress on Milestone 2
- Path to full flexibility later

**Cons:**
- Initial template extraction effort
- May duplicate some functionality

---

## Recommended Template Set

### Priority 1: Immediate Need
| Template | Source | HVAC |
|----------|--------|------|
| DataCenter_SingleZone | Custom (from sample) | CRAC w/ DX Cooling |
| DataCenter_MultiZone | Custom | Chilled Water + CRAC |
| Warehouse_Basic | DOE Prototype | Unit heaters |
| Warehouse_Manufacturing | Adapted | Heat pumps + process loads |

### Priority 2: Phase 2
| Template | Source | HVAC |
|----------|--------|------|
| Office_Small | DOE Prototype | Packaged rooftop |
| Office_Medium | DOE Prototype | VAV + chiller |
| MixedUse_OfficeWarehouse | Custom | Hybrid system |

### Priority 3: Future
| Template | Source | HVAC |
|----------|--------|------|
| Laboratory | Custom | 100% OA + fume hoods |
| Greenhouse | Custom | Passive + supplemental |
| ColdStorage | Custom | Refrigeration system |

---

## Technical Implementation Notes

### Extracting IDF from OpenStudio

```ruby
# Run measure and export IDF
require 'openstudio'

model = OpenStudio::Model::Model.new
# Apply measure...
workspace = model.toIdf
File.write('template.idf', workspace.to_s)
```

### Python IDF Modification (eppy library)

```python
from eppy import modeleditor
from eppy.modeleditor import IDF

# Load template
idf = IDF('template.idf')

# Modify building dimensions
building = idf.idfobjects['BUILDING'][0]
building.North_Axis = 45  # Rotate building

# Scale zones (pseudo-code)
for zone in idf.idfobjects['ZONE']:
    # Modify zone geometry
    ...

# Save modified model
idf.save('modified.idf')
```

### OpenStudio SDK Integration (if needed later)

```python
import subprocess
import json

def run_openstudio_measure(osw_path):
    """Run OpenStudio workflow"""
    result = subprocess.run(
        ['openstudio', 'run', '-w', osw_path],
        capture_output=True
    )
    return json.loads(result.stdout)
```

---

## Decision Matrix

| Factor | Option A (Full OS) | Option B (IDF Only) | Option C (Hybrid) |
|--------|-------------------|---------------------|-------------------|
| Complexity | High | Low | Medium |
| Flexibility | High | Low | Medium→High |
| Deployment | Complex | Simple | Simple→Medium |
| Time to Implement | Long | Short | Short start |
| Maintenance | Community | Manual | Mixed |
| **Recommendation** | Phase 3+ | Phase 1 fallback | **Phase 1-2** |

---

## Next Steps

1. **Immediate**: Download and evaluate DOE Prototype Building measure
2. **Short-term**: Create data center template from existing sample file
3. **Medium-term**: Develop Python parametric modification tools
4. **Long-term**: Evaluate full OpenStudio integration for Phase 2

---

## References

- [BCL Measures](https://bcl.nrel.gov/browse/measures)
- [OpenStudio Measure Writing Guide](https://nrel.github.io/OpenStudio-user-documentation/reference/measure_writing_guide/)
- [DOE Commercial Reference Buildings](https://www.energy.gov/eere/buildings/commercial-reference-buildings)
- [eppy - Python IDF Editor](https://eppy.readthedocs.io/)
- [OpenStudio SDK](https://openstudio.net/)
