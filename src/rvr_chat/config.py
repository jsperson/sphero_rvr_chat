"""Configuration management for RVR Chat."""

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = {
    "model": "qwen2.5:7b",
    "mcp_command": ["/home/jsperson/source/sphero_rvr_mcp/.venv/bin/python", "-m", "sphero_rvr_mcp"],
    "max_history": 100,
    "temperature": 0.7,
    "auto_connect_rvr": True,
}

def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = Path.home() / ".rvr-chat"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_history_dir() -> Path:
    """Get the conversation history directory path."""
    history_dir = get_config_dir() / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir


def get_config_path() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load configuration from file, creating defaults if needed."""
    config_path = get_config_path()

    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        # Merge with defaults
        config = {**DEFAULT_CONFIG, **user_config}
    else:
        config = DEFAULT_CONFIG.copy()
        save_config(config)

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
