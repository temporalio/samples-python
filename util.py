"""
Utility module
"""
from pathlib import Path

def get_temporal_config_path() -> Path:
    """
    Get the path to the temporal.toml configuration file.
    
    This assumes the temporal.toml file is in the root of the samples-python repository.
    
    Returns:
        Path to temporal.toml
    """
    return Path(__file__).resolve().parent / "temporal.toml" 