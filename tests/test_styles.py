import ast
import os
import unittest
from pathlib import Path

class StyleChecker(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.violations = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name == 'setStyleSheet':
                is_allowed = False
                filename = os.path.basename(self.filepath)
                
                # Allow the global stylesheet application
                if filename == 'main.py':
                    if len(node.args) == 1:
                        arg = node.args[0]
                        # Check if the argument is a Name matching 'qss' or 'DARK_STYLE'
                        if isinstance(arg, ast.Name) and arg.id in ('qss', 'DARK_STYLE'):
                            is_allowed = True
                elif filename == 'styles.py':
                    if len(node.args) == 1:
                        arg = node.args[0]
                        # Check if the argument is a Name matching 'qss'
                        if isinstance(arg, ast.Name) and arg.id == 'qss':
                            is_allowed = True
                
                if not is_allowed:
                    self.violations.append((node.lineno, node.col_offset, "Forbidden inline setStyleSheet call found."))
            
            elif attr_name == 'setFont':
                is_allowed = False
                # If setFont is called on QPainter or QTreeWidgetItem, it is allowed
                value = node.func.value
                if isinstance(value, ast.Name) and value.id in ('painter', 'item'):
                    is_allowed = True
                elif isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == 'self' and value.attr in ('painter', 'item'):
                    is_allowed = True
                
                if not is_allowed:
                    self.violations.append((node.lineno, node.col_offset, "Forbidden inline setFont call found on a widget."))
                
        self.generic_visit(node)

class TestStyleRules(unittest.TestCase):
    def test_no_inline_styling_calls(self):
        """Verify that no inline setStyleSheet or widget setFont calls exist in the python code.
        All UI styling and font definitions must be handled via the centralized resources/styles/dark.qss file.
        """
        project_root = Path(__file__).resolve().parent.parent / "src"
        violations_found = []
        
        # Scan all python files in project root (excluding tests, .venv, etc.)
        for root, dirs, files in os.walk(project_root):
            # Skip tests directory, virtual envs, build, etc.
            if any(p in Path(root).parts for p in ('tests', '.git', '__pycache__', '.venv', 'venv', 'env', 'build', 'dist')):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        tree = ast.parse(content, filename=filepath)
                        checker = StyleChecker(filepath)
                        checker.visit(tree)
                        for lineno, col, reason in checker.violations:
                            rel_path = os.path.relpath(filepath, project_root)
                            violations_found.append(f"{rel_path}:{lineno} - {reason}")
                    except Exception as e:
                        self.fail(f"Failed to parse {filepath}: {e}")
                        
        if violations_found:
            msg = "\n".join(violations_found)
            self.fail(
                f"Style violations found! All styling must be handled via resources/styles/dark.qss.\n"
                f"Do not use inline setStyleSheet or setFont in Python UI code.\n"
                f"Violations:\n{msg}"
            )
