"""
Central location for project-wide constants and path definitions.
Avoids circular imports and duplication of path logic.
"""

from pathlib import Path

# Project structure
ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"
DATA_DIR = ROOT_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
