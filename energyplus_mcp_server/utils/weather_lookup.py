"""
Weather file lookup by latitude/longitude using PVGIS API

EnergyPlus Model Context Protocol Server (EnergyPlus-MCP)
Copyright (c) 2025, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of
any required approvals from the U.S. Dept. of Energy). All rights reserved.

See License.txt in the parent directory for license details.
"""

import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# PVGIS API configuration
PVGIS_BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3"
PVGIS_TMY_ENDPOINT = f"{PVGIS_BASE_URL}/tmy"

# PVGIS coverage regions and their databases
PVGIS_DATABASES = {
    "PVGIS-SARAH3": "Europe, Central Asia, Africa, parts of South America",
    "PVGIS-SARAH2": "Europe, Asia, Africa, South America below 20°S",
    "PVGIS-NSRDB": "Americas above 20°S",
    "PVGIS-ERA5": "Worldwide coverage (lower resolution)"
}


class WeatherLookupError(Exception):
    """Exception raised when weather lookup fails"""
    pass


class WeatherLookup:
    """
    Weather file lookup service using PVGIS API.

    Fetches TMY (Typical Meteorological Year) weather data for any location
    and returns it in EnergyPlus EPW format.

    Coverage:
    - Europe, Africa, Asia: High-resolution satellite data (PVGIS-SARAH3)
    - Americas: NSRDB data
    - Worldwide: ERA5 reanalysis data (lower resolution fallback)

    API Documentation:
    https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
    """

    def __init__(self, output_dir: str, timeout: int = 60):
        """
        Initialize the weather lookup service.

        Args:
            output_dir: Directory to save downloaded weather files
            timeout: Request timeout in seconds
        """
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"WeatherLookup initialized with output_dir: {self.output_dir}")

    def fetch_weather_by_location(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None,
        use_horizon: bool = True,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch weather data for a given latitude/longitude and save as EPW file.

        Args:
            latitude: Latitude in decimal degrees (-90 to 90, positive = North)
            longitude: Longitude in decimal degrees (-180 to 180, positive = East)
            location_name: Optional name for the location (used in filename)
            use_horizon: Include effects of local horizon (default: True)
            start_year: First year for TMY calculation (optional)
            end_year: Last year for TMY calculation (optional, must be >= start_year + 10)

        Returns:
            Dict containing:
                - success: bool
                - epw_path: Path to saved EPW file
                - location: Dict with lat, lon, elevation
                - metadata: Dict with data source info
                - error: Error message if failed

        Raises:
            WeatherLookupError: If the API request fails
        """
        # Validate inputs
        if not -90 <= latitude <= 90:
            raise WeatherLookupError(f"Latitude must be between -90 and 90, got {latitude}")
        if not -180 <= longitude <= 180:
            raise WeatherLookupError(f"Longitude must be between -180 and 180, got {longitude}")

        logger.info(f"Fetching weather data for lat={latitude}, lon={longitude}")

        # Build API request parameters
        params = {
            "lat": latitude,
            "lon": longitude,
            "outputformat": "epw",
            "browser": 0  # Return as stream
        }

        if use_horizon:
            params["usehorizon"] = 1

        if start_year:
            params["startyear"] = start_year
        if end_year:
            params["endyear"] = end_year

        try:
            # Make API request
            response = requests.get(
                PVGIS_TMY_ENDPOINT,
                params=params,
                timeout=self.timeout
            )

            # Check for errors
            if response.status_code != 200:
                error_msg = f"PVGIS API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = f"PVGIS API error: {error_data['message']}"
                except Exception:
                    error_msg = f"PVGIS API error: {response.text[:200]}"
                raise WeatherLookupError(error_msg)

            # Get EPW content
            epw_content = response.text

            # Validate EPW content
            if not epw_content.startswith("LOCATION"):
                raise WeatherLookupError(f"Invalid EPW response from PVGIS: {epw_content[:100]}")

            # Fix EPW content for EnergyPlus compatibility
            epw_content = self._fix_epw_for_energyplus(
                epw_content, latitude, longitude, location_name
            )

            # Generate filename
            if location_name:
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in location_name)
                filename = f"{safe_name}_{latitude:.4f}_{longitude:.4f}.epw"
            else:
                filename = f"weather_{latitude:.4f}_{longitude:.4f}.epw"

            epw_path = self.output_dir / filename

            # Save EPW file
            with open(epw_path, "w", encoding="utf-8") as f:
                f.write(epw_content)

            logger.info(f"Weather file saved to: {epw_path}")

            # Parse metadata from EPW header
            metadata = self._parse_epw_header(epw_content)

            return {
                "success": True,
                "epw_path": str(epw_path),
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "elevation": metadata.get("elevation", 0),
                    "name": location_name or f"Location ({latitude:.4f}, {longitude:.4f})"
                },
                "metadata": metadata,
                "api_source": "PVGIS v5.3",
                "timestamp": datetime.now().isoformat()
            }

        except requests.exceptions.Timeout:
            raise WeatherLookupError(f"PVGIS API request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise WeatherLookupError(f"Network error fetching weather data: {str(e)}")

    def _fix_epw_for_energyplus(
        self,
        epw_content: str,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None
    ) -> str:
        """
        Fix PVGIS EPW content for EnergyPlus compatibility.

        PVGIS EPW files have some formatting issues that cause EnergyPlus to fail:
        1. LOCATION line has 'unknown' for city/state/country
        2. DATA PERIODS line may have incorrect date format
        3. Missing timezone offset

        Args:
            epw_content: Raw EPW content from PVGIS
            latitude: Latitude used for the request
            longitude: Longitude used for the request
            location_name: Optional location name

        Returns:
            Fixed EPW content string
        """
        lines = epw_content.split("\n")
        fixed_lines = []

        # Calculate timezone from longitude (approximate)
        timezone = round(longitude / 15)

        for line in lines:
            if line.startswith("LOCATION"):
                # Fix LOCATION line
                # Format: LOCATION,City,State,Country,Source,WMO,Lat,Lon,TZ,Elev
                parts = line.split(",")
                if len(parts) >= 10:
                    city = location_name or f"Lat{latitude:.2f}_Lon{longitude:.2f}"
                    state = "-"
                    country = "PVGIS"
                    source = parts[4] if len(parts) > 4 else "PVGIS-ERA5"
                    wmo = parts[5] if len(parts) > 5 else "999999"
                    lat = parts[6] if len(parts) > 6 else str(latitude)
                    lon = parts[7] if len(parts) > 7 else str(longitude)
                    tz = str(timezone)
                    elev = parts[9] if len(parts) > 9 else "0"

                    fixed_line = f"LOCATION,{city},{state},{country},{source},{wmo},{lat},{lon},{tz},{elev}"
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)

            elif line.startswith("DATA PERIODS"):
                # Fix DATA PERIODS line
                # Format: DATA PERIODS,NumPeriods,NumRecordsPerHour,Name,StartDay,StartDate,EndDate
                # PVGIS uses "12/31" but EnergyPlus needs proper format
                parts = line.split(",")
                if len(parts) >= 7:
                    # Reconstruct with proper date format
                    # EnergyPlus expects: DATA PERIODS,1,1,Data,Sunday, 1/ 1,12/31
                    fixed_line = f"DATA PERIODS,1,1,Data,Sunday, 1/ 1,12/31"
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)

            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _parse_epw_header(self, epw_content: str) -> Dict[str, Any]:
        """Parse metadata from EPW file header"""
        metadata = {}
        lines = epw_content.split("\n")

        for line in lines[:8]:  # Header is first 8 lines
            if line.startswith("LOCATION"):
                parts = line.split(",")
                if len(parts) >= 10:
                    metadata["city"] = parts[1]
                    metadata["state"] = parts[2]
                    metadata["country"] = parts[3]
                    metadata["data_source"] = parts[4]
                    metadata["wmo_id"] = parts[5]
                    try:
                        metadata["latitude"] = float(parts[6])
                        metadata["longitude"] = float(parts[7])
                        metadata["timezone"] = float(parts[8])
                        metadata["elevation"] = float(parts[9])
                    except (ValueError, IndexError):
                        pass
            elif line.startswith("COMMENTS 1"):
                metadata["comments1"] = line.replace("COMMENTS 1,", "")
            elif line.startswith("COMMENTS 2"):
                metadata["comments2"] = line.replace("COMMENTS 2,", "")
            elif line.startswith("DATA PERIODS"):
                metadata["data_periods"] = line.replace("DATA PERIODS,", "")

        return metadata

    def get_coverage_info(self) -> Dict[str, str]:
        """
        Get information about PVGIS coverage regions.

        Returns:
            Dict mapping database names to coverage descriptions
        """
        return PVGIS_DATABASES.copy()

    def check_location_coverage(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Check which PVGIS databases cover a given location.

        Note: This is an approximation based on documented coverage.
        The actual API will automatically select the best available database.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Dict with coverage information
        """
        coverage = {
            "latitude": latitude,
            "longitude": longitude,
            "available_databases": [],
            "recommended_database": None,
            "notes": []
        }

        # Check PVGIS-SARAH3 coverage (Europe, Africa, Central Asia)
        if -35 <= latitude <= 65 and -20 <= longitude <= 70:
            coverage["available_databases"].append("PVGIS-SARAH3")
            coverage["notes"].append("High-resolution satellite data available")

        # Check PVGIS-NSRDB coverage (Americas)
        if latitude >= -20 and -170 <= longitude <= -20:
            coverage["available_databases"].append("PVGIS-NSRDB")
            coverage["notes"].append("NREL NSRDB data available")

        # ERA5 covers everywhere
        coverage["available_databases"].append("PVGIS-ERA5")

        # Set recommended database
        if coverage["available_databases"]:
            coverage["recommended_database"] = coverage["available_databases"][0]

        if not coverage["available_databases"][:-1]:  # Only ERA5
            coverage["notes"].append("Only ERA5 reanalysis data available (lower resolution)")

        return coverage


def get_weather_for_location(
    latitude: float,
    longitude: float,
    output_dir: str,
    location_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to fetch weather data for a location.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        output_dir: Directory to save the EPW file
        location_name: Optional name for the location

    Returns:
        Dict with weather file path and metadata
    """
    lookup = WeatherLookup(output_dir)
    return lookup.fetch_weather_by_location(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name
    )
