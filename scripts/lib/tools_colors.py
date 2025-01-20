"""Color configuration loader for tools.py"""
import os
from typing import Dict

# Use tomllib from stdlib, fallback to tomli for older Python versions
try:
    import tomllib
except ImportError:
    # For Python < 3.11
    try:
        import tomli as tomllib
    except ImportError:
        # If neither is available, we'll use default colors
        tomllib = None

def load_colors() -> Dict[str, str]:
    """
    Load color configuration from TOML files.
    Checks for custom colors first, falls back to defaults.
    Returns default colors if TOML parsing is unavailable.
    """
    # Default colors if no files exist or TOML parsing unavailable
    colors = {
        "COLOR_PROMPT": "cyan",
        "COLOR_OPTION": "magenta",
        "COLOR_OUTPUT": "green",
        "COLOR_OUTPUT_VALUE": "yellow",
        "COLOR_SUCCESS": "green",
        "COLOR_ERROR": "red",
        "COLOR_WARNING": "yellow",
        "COLOR_INFO": "blue",
        "COLOR_BOX_TEXT": "white"
    }

    # If TOML parsing is not available, return defaults
    if tomllib is None:
        return colors

    # Look for custom colors first
    config_path = os.path.dirname(__file__)
    custom_file = os.path.join(config_path, "tools_colors_custom.toml")
    default_file = os.path.join(config_path, "tools_colors.toml")

    try:
        if os.path.exists(custom_file):
            with open(custom_file, "rb") as f:
                colors.update(tomllib.load(f))
        elif os.path.exists(default_file):
            with open(default_file, "rb") as f:
                colors.update(tomllib.load(f))
    except Exception:
        pass  # Use default colors on any error

    return colors

# Export color constants
globals().update(load_colors())

# Make colors available for import
__all__ = [
    "COLOR_PROMPT",
    "COLOR_OPTION",
    "COLOR_OUTPUT",
    "COLOR_OUTPUT_VALUE",
    "COLOR_SUCCESS",
    "COLOR_ERROR",
    "COLOR_WARNING",
    "COLOR_INFO",
    "COLOR_BOX_TEXT"
]
