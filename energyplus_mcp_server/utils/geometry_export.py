"""
3D Geometry Export Service for EnergyPlus MCP Server

Exports IDF building geometry to 3D formats (OBJ, glTF) for visualization
in Blender, web viewers, and other 3D applications.

Pipeline:
    IDF → GeomEppy (OBJ export) → Trimesh (glTF conversion) → Output files

Supported output formats:
    - OBJ (.obj + .mtl) - Wavefront, widely supported
    - glTF (.glb) - Modern web-ready format, single binary file
    - glTF (.gltf + .bin) - glTF with separate binary

Usage:
    from energyplus_mcp_server.utils.geometry_export import GeometryExportService

    service = GeometryExportService(idd_path="/path/to/Energy+.idd")
    result = service.export_to_gltf(idf_path, output_dir)
"""

# Python 3.10+ compatibility fix for geomeppy
# geomeppy uses deprecated collections imports - patch them before importing
import collections
import collections.abc
# Add aliases for deprecated names
if not hasattr(collections, 'MutableSequence'):
    collections.MutableSequence = collections.abc.MutableSequence
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, 'MutableMapping'):
    collections.MutableMapping = collections.abc.MutableMapping
if not hasattr(collections, 'Sequence'):
    collections.Sequence = collections.abc.Sequence
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable

import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Literal

logger = logging.getLogger(__name__)

# Output format types
OutputFormat = Literal["obj", "glb", "gltf"]


class GeometryExportError(Exception):
    """Custom exception for geometry export errors"""
    pass


class GeometryExportService:
    """Service for exporting IDF geometry to 3D formats"""

    def __init__(self, idd_path: Optional[str] = None):
        """
        Initialize the geometry export service.

        Args:
            idd_path: Path to EnergyPlus IDD file. If not provided,
                     attempts to auto-detect from environment or config.
        """
        self.idd_path = idd_path
        self._idd_set = False

    def _ensure_idd(self):
        """Ensure IDD path is set for geomeppy"""
        if self._idd_set:
            return

        try:
            from geomeppy import IDF
        except ImportError:
            raise GeometryExportError(
                "geomeppy not installed. Install with: pip install geomeppy"
            )

        # Get IDD path from config if not provided
        if not self.idd_path:
            try:
                from energyplus_mcp_server.config import get_config
                config = get_config()
                self.idd_path = config.energyplus.idd_path
            except Exception as e:
                raise GeometryExportError(
                    f"Could not determine IDD path: {e}. "
                    "Please provide idd_path parameter."
                )

        if not self.idd_path or not Path(self.idd_path).exists():
            raise GeometryExportError(
                f"IDD file not found: {self.idd_path}"
            )

        # Set IDD for geomeppy
        IDF.setiddname(str(self.idd_path))
        self._idd_set = True
        logger.info(f"GeomEppy IDD set to: {self.idd_path}")

    def export_to_obj(
        self,
        idf_path: str,
        output_dir: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export IDF geometry to OBJ format.

        Args:
            idf_path: Path to the IDF file
            output_dir: Directory for output files (default: same as IDF)
            output_name: Base name for output files (default: IDF filename)

        Returns:
            Dict with:
                - success: bool
                - obj_path: Path to .obj file
                - mtl_path: Path to .mtl file
                - message: Status message
        """
        self._ensure_idd()

        from geomeppy import IDF

        idf_path = Path(idf_path)
        if not idf_path.exists():
            raise GeometryExportError(f"IDF file not found: {idf_path}")

        # Determine output paths
        output_dir = Path(output_dir) if output_dir else idf_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = output_name or idf_path.stem
        obj_path = output_dir / f"{output_name}.obj"
        mtl_path = output_dir / f"{output_name}.mtl"

        try:
            # Load IDF and export to OBJ
            logger.info(f"Loading IDF: {idf_path}")
            idf = IDF(str(idf_path))

            # geomeppy to_obj creates file without .obj extension
            obj_base = obj_path.with_suffix('')
            logger.info(f"Exporting to OBJ: {obj_path}")
            idf.to_obj(str(obj_base))

            # geomeppy creates file without extension - rename if needed
            obj_no_ext = obj_base
            if obj_no_ext.exists() and not obj_path.exists():
                obj_no_ext.rename(obj_path)
                logger.debug(f"Renamed {obj_no_ext} to {obj_path}")

            # Verify files were created
            if not obj_path.exists():
                # Maybe it was created without extension
                if obj_no_ext.exists():
                    obj_no_ext.rename(obj_path)
                else:
                    raise GeometryExportError("OBJ file was not created")

            result = {
                "success": True,
                "obj_path": str(obj_path),
                "mtl_path": str(mtl_path) if mtl_path.exists() else None,
                "message": f"Successfully exported to {obj_path}"
            }

            logger.info(f"OBJ export complete: {obj_path}")
            return result

        except Exception as e:
            logger.error(f"OBJ export failed: {e}")
            raise GeometryExportError(f"Failed to export OBJ: {e}")

    def export_to_gltf(
        self,
        idf_path: str,
        output_dir: Optional[str] = None,
        output_name: Optional[str] = None,
        binary: bool = True
    ) -> Dict[str, Any]:
        """
        Export IDF geometry to glTF format.

        Args:
            idf_path: Path to the IDF file
            output_dir: Directory for output files (default: same as IDF)
            output_name: Base name for output files (default: IDF filename)
            binary: If True, export as .glb (single file). If False, .gltf + .bin

        Returns:
            Dict with:
                - success: bool
                - gltf_path: Path to .glb or .gltf file
                - format: "glb" or "gltf"
                - file_size_bytes: Size of the output file
                - message: Status message
        """
        try:
            import trimesh
        except ImportError:
            raise GeometryExportError(
                "trimesh not installed. Install with: pip install trimesh"
            )

        idf_path = Path(idf_path)

        # Determine output paths
        output_dir = Path(output_dir) if output_dir else idf_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = output_name or idf_path.stem

        # First export to OBJ (in temp directory)
        with tempfile.TemporaryDirectory() as temp_dir:
            obj_result = self.export_to_obj(
                idf_path=str(idf_path),
                output_dir=temp_dir,
                output_name=output_name
            )

            obj_path = obj_result["obj_path"]

            try:
                # Load OBJ with trimesh
                logger.info(f"Loading OBJ into trimesh: {obj_path}")
                mesh = trimesh.load(obj_path)

                # Rotate to correct orientation for Blender
                # EnergyPlus: Z-up, but OBJ export has Y as depth
                # Blender expects Z-up, so rotate -90° around X axis
                import numpy as np
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    np.radians(-90), [1, 0, 0]
                )
                mesh.apply_transform(rotation_matrix)
                logger.debug("Applied -90° X rotation for Blender orientation")

                # Determine output format and path
                if binary:
                    gltf_path = output_dir / f"{output_name}.glb"
                    format_type = "glb"
                else:
                    gltf_path = output_dir / f"{output_name}.gltf"
                    format_type = "gltf"

                # Export to glTF
                logger.info(f"Exporting to glTF: {gltf_path}")
                mesh.export(str(gltf_path))

                # Get file size
                file_size = gltf_path.stat().st_size

                result = {
                    "success": True,
                    "gltf_path": str(gltf_path),
                    "format": format_type,
                    "file_size_bytes": file_size,
                    "message": f"Successfully exported to {gltf_path}"
                }

                logger.info(f"glTF export complete: {gltf_path} ({file_size} bytes)")
                return result

            except Exception as e:
                logger.error(f"glTF conversion failed: {e}")
                raise GeometryExportError(f"Failed to convert to glTF: {e}")

    def export(
        self,
        idf_path: str,
        output_dir: Optional[str] = None,
        output_name: Optional[str] = None,
        formats: Optional[List[OutputFormat]] = None
    ) -> Dict[str, Any]:
        """
        Export IDF geometry to multiple formats.

        Args:
            idf_path: Path to the IDF file
            output_dir: Directory for output files (default: same as IDF)
            output_name: Base name for output files (default: IDF filename)
            formats: List of formats to export. Default: ["glb"]
                    Options: "obj", "glb", "gltf"

        Returns:
            Dict with:
                - success: bool
                - exports: Dict mapping format to export result
                - message: Status message
        """
        formats = formats or ["glb"]

        idf_path = Path(idf_path)
        output_dir = Path(output_dir) if output_dir else idf_path.parent
        output_name = output_name or idf_path.stem

        exports = {}
        errors = []

        for fmt in formats:
            try:
                if fmt == "obj":
                    exports["obj"] = self.export_to_obj(
                        idf_path=str(idf_path),
                        output_dir=str(output_dir),
                        output_name=output_name
                    )
                elif fmt == "glb":
                    exports["glb"] = self.export_to_gltf(
                        idf_path=str(idf_path),
                        output_dir=str(output_dir),
                        output_name=output_name,
                        binary=True
                    )
                elif fmt == "gltf":
                    exports["gltf"] = self.export_to_gltf(
                        idf_path=str(idf_path),
                        output_dir=str(output_dir),
                        output_name=output_name,
                        binary=False
                    )
                else:
                    errors.append(f"Unknown format: {fmt}")

            except Exception as e:
                errors.append(f"{fmt}: {str(e)}")

        success = len(exports) > 0 and len(errors) == 0

        return {
            "success": success,
            "exports": exports,
            "errors": errors if errors else None,
            "message": f"Exported {len(exports)} format(s)" + (
                f" with {len(errors)} error(s)" if errors else ""
            )
        }

    def get_geometry_info(self, idf_path: str) -> Dict[str, Any]:
        """
        Get geometry information from an IDF file without exporting.

        Args:
            idf_path: Path to the IDF file

        Returns:
            Dict with geometry statistics (zones, surfaces, vertices, etc.)
        """
        self._ensure_idd()

        from geomeppy import IDF

        idf_path = Path(idf_path)
        if not idf_path.exists():
            raise GeometryExportError(f"IDF file not found: {idf_path}")

        try:
            idf = IDF(str(idf_path))

            # Count geometry objects
            zones = idf.idfobjects.get("ZONE", [])
            surfaces = idf.idfobjects.get("BUILDINGSURFACE:DETAILED", [])
            fenestrations = idf.idfobjects.get("FENESTRATIONSURFACE:DETAILED", [])
            shadings = idf.idfobjects.get("SHADING:SITE:DETAILED", [])

            # Calculate total vertices
            total_vertices = 0
            for surface in surfaces:
                # Count vertex fields (X1, Y1, Z1, X2, Y2, Z2, ...)
                vertex_count = 0
                for i in range(1, 100):  # Max reasonable vertices
                    if hasattr(surface, f"Vertex_{i}_Xcoordinate"):
                        vertex_count += 1
                    else:
                        break
                total_vertices += vertex_count

            return {
                "idf_path": str(idf_path),
                "zones": len(zones),
                "surfaces": len(surfaces),
                "fenestrations": len(fenestrations),
                "shading_surfaces": len(shadings),
                "total_vertices": total_vertices,
                "zone_names": [z.Name for z in zones] if zones else []
            }

        except Exception as e:
            logger.error(f"Failed to get geometry info: {e}")
            raise GeometryExportError(f"Failed to read IDF geometry: {e}")
