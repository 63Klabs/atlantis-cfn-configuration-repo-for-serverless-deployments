#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-28"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

"""
Tools specific to Atlantis scripts
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import sys

import click

from .logger import Log
from .tools import Colorize, Strings

# -------------------------------------------------------------------------
# - File Name List Utilities
# -------------------------------------------------------------------------

class FileNameListUtils:

    @staticmethod
    def select_from_file_list(file_list: List[str], 
                              allow_none: Optional[bool] = False, 
                              *, 
                              heading_text="Available files",
                              prompt_text="Enter file number") -> str:
        """List available files and prompt the user to choose one.

        Args:
            file_list (List[str]): List of files to use
            allow_none (Optional[bool]): List 0. None as an option
            
        Returns:
            str: Selected file
        """

        if not file_list:
            Log.error("No files found")
            click.echo(Colorize.error("No files found"))
            if not allow_none:
                sys.exit(1)
        
        # Sort file_list for consistent ordering
        file_list.sort()

        # We want to put the filename first and pad out to make it easy to view
        selection_list = FileNameListUtils.extract_filenames_from_paths(file_list)
        max_filename = Strings.find_longest_string_length_in_column(selection_list, 0)
        max_filepath = Strings.find_longest_string_length_in_column(selection_list, 1)
        terminal_width = Strings.get_terminal_width(900)
        two_line = max_filename + max_filepath + 7 > terminal_width
        
        # Display numbered list
        click.echo(Colorize.question(f"{heading_text}:"))
        if (allow_none): click.echo(Colorize.option("0. None"))
        for idx, line_item in enumerate(selection_list, 1):
            line = ""
            if two_line:
                line = f"{idx}. {line_item[0]}\n    {line_item[1]}"
            else:
                line = f"{idx}. {Strings.pad_string(line_item[0], max_filename)} | {line_item[1]}"
            click.echo(Colorize.option(line))
        
        print()

        while True:
            try:
                default = ''

                choice = Colorize.prompt(prompt_text, default, str)
                # Check if input is a number
                sel_idx = int(choice) - 1

                min = -1 if allow_none else 0
                
                # Validate the index is within range
                if min <= sel_idx < len(selection_list):

                    selected = None

                    if(sel_idx >= 0):
                        selected = selection_list[sel_idx][1]
                                                
                    return selected
                else:
                    click.echo(Colorize.error(f"Please enter a number between {min} and {len(selection_list)}"))
            except ValueError:
                click.echo(Colorize.error("Please enter a valid number"))
            except KeyboardInterrupt:
                click.echo(Colorize.info("File selection cancelled"))
                sys.exit(1)

        
    @staticmethod
    def extract_filenames_from_paths(paths: List[str]) -> List[List[str]]:
        """Takes a list of S3 URLs and returns a list of [filename, full_path] pairs.

        Args:
            paths (List[str]): List of S3 URLs (e.g., ['s3://bucket/path/file.zip', ...])

        Returns:
            List[List[str]]: List of [filename, full_path] pairs maintaining original order

        Example:
            Input: ['s3://bucket/path/file.zip', 's3://bucket/other/doc.pdf']
            Output: [['file.zip', 's3://bucket/path/file.zip'], 
                    ['doc.pdf', 's3://bucket/other/doc.pdf']]
        """
        try:
            result = []
            for path in paths:
                # Extract the filename from the full path
                filename = path.split('/')[-1]
                # Create pair and append to result
                result.append([filename, path])
            return result
        except Exception as e:
            Log.error(f"Error processing S3 URLs: {str(e)}")
            raise

# -------------------------------------------------------------------------
# - Configuration Loader
# -------------------------------------------------------------------------

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
