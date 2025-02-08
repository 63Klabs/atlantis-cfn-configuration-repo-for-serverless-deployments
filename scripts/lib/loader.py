import json
from pathlib import Path
from typing import Dict

from .logger import Log

class ConfigLoader:
    def __init__(self, settings_dir: Path, prefix: str = "", project_id: str = "", infra_type: str = ""):
        """Initialize the ConfigLoader
        
        Args:
            settings_dir (Path): Base directory for configuration files
            prefix (str, optional): Configuration prefix. Defaults to "".
            project_id (str, optional): Project identifier. Defaults to "".
            infra_type (str, optional): Infrastructure type. Defaults to "".
        """
        self.settings_dir = settings_dir
        self.prefix = prefix
        self.project_id = project_id
        self.infra_type = infra_type

    def get_settings_dir(self) -> Path:
        """Get the settings directory path
        
        Returns:
            Path: Path to settings directory
        """
        return self.settings_dir

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Recursively update a dictionary
        
        Args:
            base_dict (Dict): Base dictionary to update
            update_dict (Dict): Dictionary with updates to apply
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def load_settings(self) -> Dict:
        """Load settings.json
        
        Returns:
            Dict: Settings dictionary from the JSON file or empty dict if file doesn't exist
            
        Raises:
            JSONDecodeError: If the settings file contains invalid JSON
            PermissionError: If the settings file cannot be accessed due to permissions
        """
        settings_file = self.get_settings_dir() / "settings.json"
        
        try:
            if settings_file.exists():
                with open(settings_file) as f:
                    try:
                        settings = json.load(f)
                        if not isinstance(settings, dict):
                            raise ValueError("Settings must be a JSON object")
                        return settings
                    except json.JSONDecodeError as e:
                        raise json.JSONDecodeError(
                            f"Invalid JSON in settings file: {str(e)}", 
                            e.doc, 
                            e.pos
                        )
            else:
                return {}
                
        except PermissionError:
            raise PermissionError(f"Unable to access settings file: {settings_file}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error loading settings: {str(e)}")

    def load_defaults(self) -> Dict:
        """Load and merge configuration files in sequence
        
        Order:
        1. defaults.json
        2. {prefix}-defaults.json
        3. {prefix}-{project_id}-defaults.json
        4. {infra_type}/defaults.json
        5. {infra_type}/{prefix}-defaults.json
        6. {infra_type}/{prefix}-{project_id}-defaults.json
        
        Returns:
            Dict: Merged configuration dictionary
        """
        defaults = {}
        
        # Define the sequence of potential config files
        config_files = [
            self.get_settings_dir() / "defaults.json",
            self.get_settings_dir() / f"{self.prefix}-defaults.json"
        ]
        
        # Add project_id specific files only if project_id exists
        if self.project_id:
            config_files.extend([
                self.get_settings_dir() / f"{self.prefix}-{self.project_id}-defaults.json",
            ])
        
        # Add infra_type specific files
        config_files.append(self.get_settings_dir() / f"{self.infra_type}" / "defaults.json")
        config_files.append(self.get_settings_dir() / f"{self.infra_type}" / f"{self.prefix}-defaults.json")
        
        # Add project_id specific files in infra_type directory
        if self.project_id:
            config_files.append(
                self.get_settings_dir() / f"{self.infra_type}" / f"{self.prefix}-{self.project_id}-defaults.json"
            )
        
        # Load each config file in sequence if it exists
        for config_file in config_files:
            try:
                if config_file.exists():
                    with open(config_file) as f:
                        # Deep update defaults with new values
                        new_config = json.load(f)
                        self._deep_update(defaults, new_config)
                        Log.info(f"Loaded config from '{config_file}'")
            except json.JSONDecodeError as e:
                Log.error(f"Error parsing JSON from {config_file}: {e}")
            except Exception as e:
                Log.error(f"Error loading config file {config_file}: {e}")
        
        return defaults
