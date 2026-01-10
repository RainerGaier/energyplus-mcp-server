"""
Configuration management for EnergyPlus MCP Server

EnergyPlus Model Context Protocol Server (EnergyPlus-MCP)
Copyright (c) 2025, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of
any required approvals from the U.S. Dept. of Energy). All rights reserved.

See License.txt in the parent directory for license details.
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


# Determine project root (parent of the energyplus_mcp_server package)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def _is_windows() -> bool:
    """Check if running on Windows"""
    return sys.platform == "win32"


def _get_platform_defaults() -> Dict[str, Any]:
    """Get platform-appropriate default paths and settings"""
    if _is_windows():
        # Windows defaults
        # Check common EnergyPlus installation locations
        possible_ep_paths = [
            Path("C:/EnergyPlusV25-2-0"),
            Path("C:/Program Files/EnergyPlusV25-2-0"),
            Path("C:/Program Files (x86)/EnergyPlusV25-2-0"),
            Path.home() / "EnergyPlusV25-2-0",
        ]

        ep_install = None
        for path in possible_ep_paths:
            if path.exists():
                ep_install = str(path)
                break

        if ep_install is None:
            ep_install = "C:/EnergyPlusV25-2-0"  # Default even if not found

        return {
            "energyplus_install": ep_install,
            "workspace_root": str(PROJECT_ROOT),
            "temp_dir": os.environ.get("TEMP", os.environ.get("TMP", "C:/Temp")),
            "executable_name": "energyplus.exe",
        }
    else:
        # Linux/Docker defaults
        return {
            "energyplus_install": "/app/software/EnergyPlusV25-2-0",
            "workspace_root": "/workspace/energyplus-mcp-server",
            "temp_dir": "/tmp",
            "executable_name": "energyplus",
        }


@dataclass
class EnergyPlusConfig:
    """EnergyPlus-specific configuration"""
    idd_path: str = ""
    installation_path: str = ""
    executable_path: str = ""
    version: str = "25.2.0"
    weather_data_path: str = ""
    default_weather_file: str = ""
    example_files_path: str = ""


@dataclass
class PathConfig:
    """Path configuration"""
    workspace_root: str = ""
    sample_files_path: str = ""
    temp_dir: str = ""
    output_dir: str = ""

    def __post_init__(self):
        """Set default paths after initialization using platform-appropriate values"""
        defaults = _get_platform_defaults()

        # Set workspace root from env var or platform default
        if not self.workspace_root:
            self.workspace_root = os.environ.get(
                "MCP_WORKSPACE_ROOT",
                defaults["workspace_root"]
            )

        # Set temp directory from env var or platform default
        if not self.temp_dir:
            self.temp_dir = os.environ.get(
                "MCP_TEMP_DIR",
                defaults["temp_dir"]
            )

        # Set output directory from env var or derive from workspace
        if not self.output_dir:
            self.output_dir = os.environ.get(
                "MCP_OUTPUT_DIR",
                os.path.join(self.workspace_root, "outputs")
            )

        # Set sample files path from env var or derive from workspace
        if not self.sample_files_path:
            self.sample_files_path = os.environ.get(
                "MCP_SAMPLE_FILES_PATH",
                os.path.join(self.workspace_root, "sample_files")
            )


@dataclass
class ServerConfig:
    """Server configuration"""
    name: str = "energyplus-mcp-server"
    version: str = "0.1.0"
    log_level: str = "INFO"
    simulation_timeout: int = 300  # seconds
    tool_timeout: int = 60  # seconds


@dataclass
class Config:
    """Main configuration class"""
    energyplus: EnergyPlusConfig = field(default_factory=EnergyPlusConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    debug_mode: bool = False
    
    def __post_init__(self):
        """Set up configuration after initialization"""
        self._setup_energyplus_paths()
        self._setup_logging()
        self._validate_config()

    def _setup_energyplus_paths(self):
        """Set up EnergyPlus paths from environment variables or platform defaults"""
        defaults = _get_platform_defaults()

        # Determine EnergyPlus installation path
        # Priority: EPLUS_INSTALL_PATH env var > EPLUS_IDD_PATH parent dir > platform default
        ep_install_path = os.getenv('EPLUS_INSTALL_PATH')
        ep_idd_path = os.getenv('EPLUS_IDD_PATH')

        if ep_install_path:
            # Explicit installation path provided
            self.energyplus.installation_path = ep_install_path
        elif ep_idd_path:
            # Derive installation path from IDD path
            self.energyplus.installation_path = os.path.dirname(ep_idd_path)
        else:
            # Use platform-appropriate default
            self.energyplus.installation_path = defaults["energyplus_install"]

        # Set IDD path
        if ep_idd_path:
            self.energyplus.idd_path = ep_idd_path
        else:
            self.energyplus.idd_path = os.path.join(
                self.energyplus.installation_path, "Energy+.idd"
            )

        # Set executable path (platform-aware: .exe on Windows)
        self.energyplus.executable_path = os.path.join(
            self.energyplus.installation_path, defaults["executable_name"]
        )

        # Set weather data path
        self.energyplus.weather_data_path = os.environ.get(
            'EPLUS_WEATHER_PATH',
            os.path.join(self.energyplus.installation_path, "WeatherData")
        )

        # Set example files path
        self.energyplus.example_files_path = os.environ.get(
            'EPLUS_EXAMPLE_FILES_PATH',
            os.path.join(self.energyplus.installation_path, "ExampleFiles")
        )

        # Set default weather file
        default_weather_filename = os.environ.get(
            'EPLUS_DEFAULT_WEATHER_FILE',
            "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
        )
        # If it's just a filename, join with weather data path
        if os.path.dirname(default_weather_filename) == "":
            self.energyplus.default_weather_file = os.path.join(
                self.energyplus.weather_data_path,
                default_weather_filename
            )
        else:
            self.energyplus.default_weather_file = default_weather_filename

    def _setup_logging(self):
        """Configure logging based on configuration"""
        log_level = getattr(logging, self.server.log_level.upper(), logging.INFO)
        
        # Configure logging format
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured: level={self.server.log_level}")

    def _validate_config(self):
        """Validate configuration and log warnings for missing components"""
        logger = logging.getLogger(__name__)
        
        # Check EnergyPlus installation
        if not os.path.exists(self.energyplus.idd_path):
            logger.warning(f"EnergyPlus IDD file not found: {self.energyplus.idd_path}")
        
        if not os.path.exists(self.energyplus.executable_path):
            logger.warning(f"EnergyPlus executable not found: {self.energyplus.executable_path}")
        
        # Check weather data
        if not os.path.exists(self.energyplus.weather_data_path):
            logger.warning(f"EnergyPlus weather data directory not found: {self.energyplus.weather_data_path}")
        
        if not os.path.exists(self.energyplus.default_weather_file):
            logger.warning(f"Default weather file not found: {self.energyplus.default_weather_file}")
        
        # Check example files
        if not os.path.exists(self.energyplus.example_files_path):
            logger.warning(f"EnergyPlus example files directory not found: {self.energyplus.example_files_path}")
        
        # Check sample files directory
        if not os.path.exists(self.paths.sample_files_path):
            logger.warning(f"Sample files directory not found: {self.paths.sample_files_path}")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.paths.output_dir, exist_ok=True)
        
        logger.info("Configuration loaded and validated successfully")

    def _setup_logging(self):
        """Set up logging configuration with both console and file handlers"""
        import logging.handlers
        from pathlib import Path

        logger = logging.getLogger(__name__)

        # Create logs directory
        log_dir = Path(self.paths.workspace_root) / "logs"
        log_dir.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.server.log_level))

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler (for stdout/stderr)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs
        # On Windows, use TimedRotatingFileHandler to avoid file locking issues
        # with uvicorn's reload feature (multiple processes accessing same file)
        if _is_windows():
            # Use a simpler FileHandler on Windows to avoid rotation locking issues
            # Files will be rotated manually or by date
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_dir / "energyplus_mcp_server.log",
                when='midnight',
                interval=1,
                backupCount=7,
                delay=True  # Delay file opening until first log message
            )
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / "energyplus_mcp_server.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Separate error log file
        if _is_windows():
            error_handler = logging.handlers.TimedRotatingFileHandler(
                log_dir / "energyplus_mcp_errors.log",
                when='midnight',
                interval=1,
                backupCount=7,
                delay=True
            )
        else:
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir / "energyplus_mcp_errors.log",
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3
            )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        logger.info(f"Logging configured: level={self.server.log_level}")
        logger.info(f"Log files: {log_dir}")

        return log_dir


def get_config() -> Config:
    """Get the global configuration instance"""
    if not hasattr(get_config, '_config'):
        get_config._config = Config()
    
    return get_config._config


def reload_config() -> Config:
    """Reload configuration (useful for testing)"""
    if hasattr(get_config, '_config'):
        delattr(get_config, '_config')
    return get_config()
