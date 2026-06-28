from PyQt6.QtGui import QIcon
from constants import RESOURCES_DIR

def load_icon(name):
    """
    Load icon by name (without extension) from resources/icons directory.
    Returns an empty QIcon if the file does not exist.
    """
    icon_path = RESOURCES_DIR / "icons" / f"{name}.png"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()

def load_icons_dict(names):
    """
    Load a dictionary of icons for a list of names.
    """
    return {name: load_icon(name) for name in names}
