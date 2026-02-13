from pathlib import Path

# Path to dark.qss file
DARK_QSS_PATH = Path(__file__).parent / "resources" / "styles" / "dark.qss"

# ==========================
# DARK_STYLE (for compatibility)
# ==========================
DARK_STYLE = "" # Initialized after StyleManager definition

import re

class StyleManager:
    """Application style manager."""
    
    @staticmethod
    def get_style(path: Path = DARK_QSS_PATH) -> str:
        """Reads style from file and replaces variables."""
        if not path.exists():
            return ""
            
        try:
            content = path.read_text(encoding="utf-8")
            
            # 1. Find all variable definitions: @var_name: #value;
            # Variables must be at the beginning of the content or after a newline
            var_pattern = re.compile(r'^@([\w-]+):\s*(.*?);', re.MULTILINE)
            variables = dict(var_pattern.findall(content))
            
            # 2. Remove variable definitions from the final QSS
            qss = var_pattern.sub("", content)
            
            # 3. Sort variables by length descending to avoid partial replacements
            # (e.g., @bg replacing part of @bg-hover)
            sorted_vars = sorted(variables.items(), key=lambda x: len(x[0]), reverse=True)
            
            # 4. Replace occurrences of @var_name with their values
            for var_name, var_value in sorted_vars:
                # Use word boundaries or ensure it doesn't match part of another variable
                # In QSS, variables are usually separated by whitespace, semicolons, etc.
                qss = qss.replace(f"@{var_name}", var_value)
                
            return qss
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
            return ""

    @staticmethod
    def apply_style(app, path: Path = DARK_QSS_PATH):
        """Applies style to application."""
        qss = StyleManager.get_style(path)
        if qss:
            app.setStyleSheet(qss)

# Initialize DARK_STYLE
DARK_STYLE = StyleManager.get_style()
