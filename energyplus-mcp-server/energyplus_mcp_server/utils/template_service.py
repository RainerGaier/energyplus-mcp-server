"""
Template service for building model generation

EnergyPlus Model Context Protocol Server (EnergyPlus-MCP)
Copyright (c) 2025, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of
any required approvals from the U.S. Dept. of Energy). All rights reserved.

See License.txt in the parent directory for license details.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Template directory relative to project root
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"


@dataclass
class TemplateInfo:
    """Information about an available template"""
    template_id: str
    name: str
    description: str
    building_type: str
    hvac_system: str
    idf_path: Path
    metadata_path: Path
    defaults: Dict[str, Any]


class TemplateServiceError(Exception):
    """Exception raised when template operations fail"""
    pass


class TemplateService:
    """
    Service for managing building templates and generating customized IDF files.

    This service:
    1. Loads template metadata from JSON files
    2. Applies building specifications to templates
    3. Generates customized IDF files for simulation
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template service.

        Args:
            templates_dir: Optional custom templates directory path
        """
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self._templates_cache: Dict[str, TemplateInfo] = {}
        self._load_templates()
        logger.info(f"TemplateService initialized with {len(self._templates_cache)} templates")

    def _load_templates(self):
        """Scan templates directory and load metadata"""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_dir}")
            return

        for category_dir in self.templates_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for json_file in category_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    template_id = metadata.get("template_id")
                    if not template_id:
                        continue

                    idf_file = metadata.get("idf_file")
                    idf_path = category_dir / idf_file

                    if not idf_path.exists():
                        logger.warning(f"IDF file not found for template {template_id}: {idf_path}")
                        continue

                    self._templates_cache[template_id] = TemplateInfo(
                        template_id=template_id,
                        name=metadata.get("name", template_id),
                        description=metadata.get("description", ""),
                        building_type=metadata.get("building_type", "unknown"),
                        hvac_system=metadata.get("hvac_system", "unknown"),
                        idf_path=idf_path,
                        metadata_path=json_file,
                        defaults=metadata.get("defaults", {})
                    )
                    logger.debug(f"Loaded template: {template_id}")

                except Exception as e:
                    logger.error(f"Error loading template from {json_file}: {e}")

    def list_templates(self, building_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available templates.

        Args:
            building_type: Optional filter by building type

        Returns:
            List of template information dictionaries
        """
        templates = []
        for template_id, info in self._templates_cache.items():
            if building_type and info.building_type != building_type:
                continue
            templates.append({
                "template_id": template_id,
                "name": info.name,
                "description": info.description,
                "building_type": info.building_type,
                "hvac_system": info.hvac_system,
                "defaults": info.defaults
            })
        return templates

    def get_template(self, template_id: str) -> TemplateInfo:
        """
        Get template information by ID.

        Args:
            template_id: Template identifier

        Returns:
            TemplateInfo object

        Raises:
            TemplateServiceError: If template not found
        """
        if template_id not in self._templates_cache:
            available = list(self._templates_cache.keys())
            raise TemplateServiceError(
                f"Template '{template_id}' not found. Available: {available}"
            )
        return self._templates_cache[template_id]

    def generate_model(
        self,
        building_spec: Dict[str, Any],
        output_path: str,
        template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a customized IDF model from a building specification.

        Args:
            building_spec: Building specification dictionary
            output_path: Path to save the generated IDF file
            template_id: Optional specific template ID (auto-selected if not provided)

        Returns:
            Dict with generation results including output path and applied parameters
        """
        # Select template based on building type if not specified
        if not template_id:
            building_type = building_spec.get("building_type", "data_center")
            template_id = self._select_template(building_type)

        template = self.get_template(template_id)
        logger.info(f"Generating model from template: {template_id}")

        # Load the template IDF
        with open(template.idf_path, "r", encoding="utf-8") as f:
            idf_content = f.read()

        # Track applied modifications
        modifications = []

        # Apply location modifications
        if "location" in building_spec:
            idf_content, loc_mods = self._apply_location(
                idf_content, building_spec["location"]
            )
            modifications.extend(loc_mods)

        # Apply geometry modifications
        if "geometry" in building_spec:
            idf_content, geo_mods = self._apply_geometry(
                idf_content, building_spec["geometry"], template.defaults.get("geometry", {})
            )
            modifications.extend(geo_mods)

        # Apply data center specific modifications
        if building_spec.get("building_type") == "data_center" and "data_center" in building_spec:
            idf_content, dc_mods = self._apply_data_center_params(
                idf_content, building_spec["data_center"]
            )
            modifications.extend(dc_mods)

        # Apply manufacturing specific modifications
        if building_spec.get("building_type") == "manufacturing" and "manufacturing" in building_spec:
            idf_content, mfg_mods = self._apply_manufacturing_params(
                idf_content, building_spec["manufacturing"]
            )
            modifications.extend(mfg_mods)

        # Apply setpoint modifications
        if "setpoints" in building_spec:
            idf_content, sp_mods = self._apply_setpoints(
                idf_content, building_spec["setpoints"]
            )
            modifications.extend(sp_mods)

        # Apply simulation options
        if "simulation_options" in building_spec:
            idf_content, sim_mods = self._apply_simulation_options(
                idf_content, building_spec["simulation_options"]
            )
            modifications.extend(sim_mods)

        # Add generation metadata as comment
        metadata_comment = self._generate_metadata_comment(building_spec, template_id)
        idf_content = metadata_comment + idf_content

        # Save the generated IDF
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(idf_content)

        logger.info(f"Generated model saved to: {output_path}")

        return {
            "success": True,
            "output_path": str(output_path),
            "template_used": template_id,
            "modifications_applied": modifications,
            "timestamp": datetime.now().isoformat()
        }

    def _select_template(self, building_type: str) -> str:
        """Select appropriate template based on building type"""
        type_mapping = {
            "data_center": "DataCenter_SingleZone",
            "manufacturing": "Manufacturing_Warehouse",
            "warehouse": "Manufacturing_Warehouse",
        }
        template_id = type_mapping.get(building_type)
        if not template_id or template_id not in self._templates_cache:
            # Default to first available template of this type
            for tid, info in self._templates_cache.items():
                if info.building_type == building_type:
                    return tid
            # Fall back to any available template
            if self._templates_cache:
                return next(iter(self._templates_cache.keys()))
            raise TemplateServiceError(f"No template available for building type: {building_type}")
        return template_id

    def _apply_location(
        self, idf_content: str, location: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply location modifications to IDF content"""
        modifications = []

        lat = location.get("latitude")
        lon = location.get("longitude")
        elev = location.get("elevation_m")
        site_name = location.get("site_name", f"Site_{lat:.2f}_{lon:.2f}")

        if lat is not None and lon is not None:
            # Calculate timezone from longitude (approximate)
            tz = round(lon / 15)

            # Find and replace Site:Location object
            location_pattern = r"(Site:Location,\s*)[^;]+(;)"

            new_location = f"""Site:Location,
    {site_name},  !- Name
    {lat},                   !- Latitude {{deg}}
    {lon},                   !- Longitude {{deg}}
    {tz},                    !- Time Zone {{hr}}
    {elev if elev else 0};   !- Elevation {{m}}"""

            if re.search(location_pattern, idf_content, re.DOTALL):
                idf_content = re.sub(location_pattern, new_location, idf_content, flags=re.DOTALL)
                modifications.append(f"Updated Site:Location to {site_name} ({lat}, {lon})")

        return idf_content, modifications

    def _apply_geometry(
        self, idf_content: str, geometry: Dict[str, Any], defaults: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply geometry modifications to IDF content"""
        modifications = []

        # Get dimensions
        length = geometry.get("length_m", defaults.get("length_m", 15.24))
        width = geometry.get("width_m", defaults.get("width_m", 15.24))
        height = geometry.get("height_m", defaults.get("height_m", 4.572))

        default_length = defaults.get("length_m", 15.24)
        default_width = defaults.get("width_m", 15.24)
        default_height = defaults.get("height_m", 4.572)

        # Calculate scale factors
        scale_x = length / default_length
        scale_y = width / default_width
        scale_z = height / default_height

        # Only modify if dimensions differ from defaults
        if abs(scale_x - 1.0) > 0.001 or abs(scale_y - 1.0) > 0.001 or abs(scale_z - 1.0) > 0.001:
            # Scale vertex coordinates in BuildingSurface:Detailed objects
            idf_content = self._scale_geometry(idf_content, scale_x, scale_y, scale_z)
            modifications.append(f"Scaled geometry to {length}m x {width}m x {height}m")

        # Apply orientation if specified
        orientation = geometry.get("orientation_deg")
        if orientation is not None:
            # Update Building north axis
            building_pattern = r"(Building,\s*[^,]+,\s*)([0-9.-]+)(,)"
            idf_content = re.sub(
                building_pattern,
                f"\\g<1>{orientation}\\3",
                idf_content,
                count=1
            )
            modifications.append(f"Set building orientation to {orientation} degrees")

        return idf_content, modifications

    def _scale_geometry(
        self, idf_content: str, scale_x: float, scale_y: float, scale_z: float
    ) -> str:
        """Scale all geometry coordinates in the IDF"""
        # This is a simplified approach - scales numeric values in vertex coordinates
        # A more robust approach would parse the IDF properly

        lines = idf_content.split("\n")
        result_lines = []
        in_surface = False
        vertex_count = 0

        for line in lines:
            if "BuildingSurface:Detailed" in line:
                in_surface = True
                vertex_count = 0
                result_lines.append(line)
                continue

            if in_surface:
                # Check for vertex coordinate lines (contain X,Y,Z pattern)
                vertex_match = re.match(
                    r"\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*([,;])\s*(!.*)?",
                    line
                )
                if vertex_match:
                    x = float(vertex_match.group(1)) * scale_x
                    y = float(vertex_match.group(2)) * scale_y
                    z = float(vertex_match.group(3)) * scale_z
                    separator = vertex_match.group(4)
                    comment = vertex_match.group(5) or ""

                    result_lines.append(f"    {x:.6f},{y:.6f},{z:.6f}{separator}  {comment}")

                    if separator == ";":
                        in_surface = False
                    continue

                if line.strip().endswith(";"):
                    in_surface = False

            result_lines.append(line)

        return "\n".join(result_lines)

    def _apply_data_center_params(
        self, idf_content: str, dc_params: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply data center specific parameters"""
        modifications = []

        # IT load parameters
        it_load_kw = dc_params.get("it_load_kw")
        rack_count = dc_params.get("rack_count")
        watts_per_rack = dc_params.get("watts_per_rack")

        if it_load_kw and rack_count:
            watts_per_rack = (it_load_kw * 1000) / rack_count
        elif rack_count and watts_per_rack:
            it_load_kw = (rack_count * watts_per_rack) / 1000

        if rack_count is not None:
            # Update Number of Units in ElectricEquipment:ITE:AirCooled
            pattern = r"(ElectricEquipment:ITE:AirCooled,.*?Watts/Unit,\s*)(\d+)(,\s*\d+)"
            idf_content = re.sub(
                pattern,
                f"\\g<1>{int(watts_per_rack) if watts_per_rack else 500},\n    {rack_count}",
                idf_content,
                flags=re.DOTALL
            )
            modifications.append(f"Set IT equipment: {rack_count} units at {watts_per_rack:.0f}W each")

        return idf_content, modifications

    def _apply_manufacturing_params(
        self, idf_content: str, mfg_params: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply manufacturing/warehouse specific parameters"""
        modifications = []

        # Process load - add as additional ElectricEquipment in BulkStorage zone
        process_load_kw = mfg_params.get("process_load_kw")
        if process_load_kw and process_load_kw > 0:
            # Convert to watts
            process_load_w = process_load_kw * 1000
            heat_fraction = mfg_params.get("process_heat_fraction", 0.5)

            # Find a good insertion point - after existing ElectricEquipment
            # Add a new ElectricEquipment object for process loads
            process_equipment = f"""
  ElectricEquipment,
    BulkStorage_ProcessLoad, !- Name
    BulkStorage,             !- Zone or ZoneList Name
    BLDG_EQUIP_SCH,          !- Schedule Name
    EquipmentLevel,          !- Design Level Calculation Method
    {process_load_w:.1f},    !- Design Level {{W}}
    ,                        !- Watts per Zone Floor Area {{W/m2}}
    ,                        !- Watts per Person {{W/person}}
    0,                       !- Fraction Latent
    {heat_fraction:.2f},     !- Fraction Radiant
    0,                       !- Fraction Lost
    Manufacturing Process Equipment;  !- End-Use Subcategory

"""
            # Insert after the last ElectricEquipment object
            # Find position before Exterior:Lights or similar
            insert_pattern = r"(  Exterior:Lights,)"
            if re.search(insert_pattern, idf_content):
                idf_content = re.sub(insert_pattern, process_equipment + r"\1", idf_content)
            else:
                # Fallback: append before OUTPUT section
                insert_pattern = r"(  Output:)"
                idf_content = re.sub(insert_pattern, process_equipment + r"\1", idf_content, count=1)

            modifications.append(f"Added process equipment load: {process_load_kw:.1f} kW ({heat_fraction*100:.0f}% radiant heat)")

        # Occupancy count
        occupancy = mfg_params.get("occupancy_count")
        if occupancy is not None:
            # The warehouse template has occupancy in the Office zone
            # For manufacturing, we might want to add people to BulkStorage too
            # For now, just note it - more complex modifications would need IDF parsing
            modifications.append(f"Note: Occupancy specified as {occupancy} people (requires manual IDF adjustment)")

        return idf_content, modifications

    def _apply_setpoints(
        self, idf_content: str, setpoints: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply temperature setpoint modifications"""
        modifications = []

        cooling_sp = setpoints.get("cooling_setpoint_c")
        heating_sp = setpoints.get("heating_setpoint_c")

        if cooling_sp is not None:
            # Update Cooling Return Air Setpoint Schedule
            pattern = r"(Cooling Return Air Setpoint Schedule.*?Until: 24:00,)([0-9.-]+)(;)"
            idf_content = re.sub(pattern, f"\\g<1>{cooling_sp}\\3", idf_content, flags=re.DOTALL)
            modifications.append(f"Set cooling setpoint to {cooling_sp}°C")

        if heating_sp is not None:
            # Update Heating Setpoint Schedule
            pattern = r"(Heating Setpoint Schedule.*?Until: 24:00,)([0-9.-]+)(;)"
            idf_content = re.sub(pattern, f"\\g<1>{heating_sp}\\3", idf_content, flags=re.DOTALL)
            modifications.append(f"Set heating setpoint to {heating_sp}°C")

        return idf_content, modifications

    def _apply_simulation_options(
        self, idf_content: str, options: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Apply simulation control options"""
        modifications = []

        run_annual = options.get("run_annual", False)
        run_design_days = options.get("run_design_days", True)
        sizing_run = options.get("sizing_run", False)

        # Find SimulationControl object and update
        sim_control_pattern = r"(SimulationControl,.*?Run Simulation for Sizing Periods,\s*)(Yes|No)(,.*?Run Simulation for Weather File Run Periods,\s*)(Yes|No)"

        new_sizing = "Yes" if run_design_days else "No"
        new_weather = "Yes" if run_annual else "No"

        replacement = f"\\g<1>{new_sizing}\\3{new_weather}"
        idf_content = re.sub(sim_control_pattern, replacement, idf_content, flags=re.DOTALL)

        modifications.append(f"Simulation: design_days={run_design_days}, annual={run_annual}")

        return idf_content, modifications

    def _generate_metadata_comment(
        self, building_spec: Dict[str, Any], template_id: str
    ) -> str:
        """Generate metadata comment block for the IDF file"""
        return f"""! =========================================================================
! Generated by EnergyPlus MCP Server
! Template: {template_id}
! Generated: {datetime.now().isoformat()}
! Project: {building_spec.get('project_name', 'Unknown')}
! Project ID: {building_spec.get('project_id', 'Unknown')}
! Location: {building_spec.get('location', {}).get('site_name', 'Unknown')}
! =========================================================================

"""


def get_template_service(templates_dir: Optional[str] = None) -> TemplateService:
    """Get or create a TemplateService instance"""
    return TemplateService(templates_dir)
