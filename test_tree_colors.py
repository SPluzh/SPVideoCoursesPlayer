"""Test script to verify tree line colors are loaded correctly."""

from pathlib import Path
from config_manager import ConfigManager
from constants import ROOT_DIR, RESOURCES_DIR, DATA_DIR

# Initialize ConfigManager
config_file = ROOT_DIR / "settings.ini"
config = ConfigManager(config_file, ROOT_DIR, DATA_DIR)

# Test get_tree_line_colors()
colors = config.get_tree_line_colors()

print(f"[OK] Loaded {len(colors)} colors from settings.ini")
print(f"\nColors list:")
for i, color in enumerate(colors, 1):
    print(f"  {i:2d}. {color}")

# Verify all colors are valid hex format
invalid_colors = [c for c in colors if not (c.startswith("#") and len(c) == 7)]
if invalid_colors:
    print(f"\n[ERROR] Found invalid color formats: {invalid_colors}")
else:
    print(f"\n[OK] All colors are valid hex format")

# Test that colors are diverse (no duplicates)
if len(colors) == len(set(colors)):
    print(f"[OK] All colors are unique")
else:
    duplicates = [c for c in colors if colors.count(c) > 1]
    print(f"[WARNING] Found duplicate colors: {set(duplicates)}")

print(f"\n[OK] Test completed successfully!")
