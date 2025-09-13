# Spectradownshift/config.py
import json
from pathlib import Path
from typing import Any

# Default profiles created if the config file is missing.
DEFAULT_PROFILES = {
    "Accurate (Scipy)": {
        "resampler": "scipy",
        "output_format": "wav",
        "cutoff": 17000
    },
    "Fast (Soxr)": {
        "resampler": "soxr",
        "output_format": "flac",
        "cutoff": 17000
    }
}

# The dictionary key for storing application-specific settings (e.g., last used paths).
SETTINGS_KEY = "_app_settings"

class ProfileManager:
    """Manages loading, saving, and updating configuration data from a JSON file."""

    def __init__(self, profiles_path: Path):
        """
        Initializes the manager with the path to the configuration file.

        Args:
            profiles_path: A Path object pointing to the profiles.json file.
        """
        self.path = profiles_path
        self.config_data = self._load_or_create()

    def _load_or_create(self) -> dict:
        """Loads a config from the JSON file, or creates a default one if it's missing or corrupt."""
        if not self.path.exists():
            return self._create_default_config()
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Basic validation to ensure the config structure is intact.
            if "profiles" not in data or SETTINGS_KEY not in data:
                raise KeyError("Required keys are missing in config.")
            return data
        except (json.JSONDecodeError, KeyError):
            print(f"Warning: '{self.path.name}' is corrupt or invalid. Recreating with defaults.")
            return self._create_default_config()

    def _create_default_config(self) -> dict:
        """Creates a default configuration structure and writes it to the file."""
        print(f"Creating '{self.path.name}' with default settings...")
        default_data = {
            "profiles": DEFAULT_PROFILES,
            SETTINGS_KEY: {"last_input_path": "", "last_output_path": ""}
        }
        self._write_to_file(default_data)
        return default_data
            
    def _write_to_file(self, data: dict) -> None:
        """Writes the entire configuration dictionary to the JSON file."""
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_profiles(self) -> dict:
        """Returns the dictionary of all saved profiles."""
        return self.config_data.get("profiles", {})

    def save_profile(self, name: str, settings: dict) -> None:
        """Saves a new profile or updates an existing one."""
        self.config_data["profiles"][name] = settings
        self._write_to_file(self.config_data)
        print(f"Profile '{name}' has been saved.")

    def delete_profile(self, name: str) -> bool:
        """
        Deletes a profile by its name.

        Args:
            name: The name of the profile to delete.

        Returns:
            True if the profile was deleted, False otherwise.
        """
        if name in self.config_data["profiles"]:
            del self.config_data["profiles"][name]
            self._write_to_file(self.config_data)
            print(f"Profile '{name}' has been deleted.")
            return True
        return False
        
    def get_app_settings(self) -> dict:
        """Returns the application-specific settings dictionary."""
        return self.config_data.get(SETTINGS_KEY, {})

    def save_app_setting(self, key: str, value: Any) -> None:
        """
        Saves a single application setting, like a recently used path.

        Args:
            key: The setting key to save.
            value: The value of the setting.
        """
        self.config_data.setdefault(SETTINGS_KEY, {})[key] = value
        self._write_to_file(self.config_data)