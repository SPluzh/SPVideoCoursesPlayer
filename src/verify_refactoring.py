
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

print("Verifying refactoring changes...")

try:
    print("1. Checking constants.py...")
    import constants
    print(f"   ROOT_DIR: {constants.ROOT_DIR}")
    print(f"   RESOURCES_DIR: {constants.RESOURCES_DIR}")
    
    print("2. Checking utils.py...")
    import utils
    if not hasattr(utils, 'resolve_binary_path'):
        raise ImportError("resolve_binary_path missing in utils")
    if not hasattr(utils, 'setup_encoding'):
        raise ImportError("setup_encoding missing in utils")
    print("   Utils functions present.")
    
    print("3. Checking progress_dialog.py...")
    import progress_dialog
    if not hasattr(progress_dialog, 'BaseProgressDialog'):
        raise ImportError("BaseProgressDialog missing in progress_dialog")
    if not hasattr(progress_dialog, 'ScanProgressDialog'):
        raise ImportError("ScanProgressDialog missing in progress_dialog")
    print("   ProgressDialog classes present.")

    print("4. Checking settings_dialog.py...")
    import settings_dialog
    # Check if we can instantiate it (headless check tricky for QDialog, just check imports)
    print("   settings_dialog imported successfully.")
    
    print("5. Checking main.py imports...")
    # diverse imports
    import main
    print("   main.py imported successfully.")

    print("\nSUCCESS: All refactored modules verify correctly!")

except Exception as e:
    print(f"\nFAILURE: {e}")
    import traceback
    traceback.print_exc()
