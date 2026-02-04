from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QButtonGroup, QDialogButtonBox, QGridLayout
from translator import tr

class MarkerDialog(QDialog):
    """Simple dialog to add/edit a marker."""
    def __init__(self, parent=None, timestamp=0.0, label="", color="#FFD700"):
        super().__init__(parent)
        print(f"DEBUG: MarkerDialog init, timestamp={timestamp}") # DEBUG
        self.setWindowTitle(tr('player.add_marker_title'))
        self.setFixedWidth(350)
        self.selected_color = color
        
        layout = QVBoxLayout(self)
        
        info = QLabel(f"{tr('player.marker_timestamp')}: {self.format_time(timestamp)}")
        layout.addWidget(info)
        
        self.input = QLineEdit()
        self.input.setText(label)
        self.input.setPlaceholderText(tr('player.marker_label_placeholder'))
        layout.addWidget(self.input)

        # Color selection
        layout.addWidget(QLabel(f"{tr('player.marker_color') or 'Color'}:"))
        
        self.color_group = QButtonGroup(self)
        colors = [
            "#FFD700", "#FF4136", "#2ECC40", "#0074D9", "#B10DC9", "#FF851B",
            "#7FDBFF", "#F012BE", "#01FF70", "#39CCCC", "#85144b", "#AAAAAA"
        ]
        
        color_grid = QGridLayout()
        color_grid.setSpacing(5)
        
        for i, c in enumerate(colors):
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCheckable(True)
            
            # Styling: 3px radius, border matching app style
            style = f"background-color: {c}; border: 1px solid #808080; border-radius: 3px;"
            if c == color:
                btn.setChecked(True)
                style = f"background-color: {c}; border: 2px solid white; border-radius: 3px;"
            
            btn.setStyleSheet(style)
            btn.setProperty("color_val", c)
            btn.clicked.connect(self._on_color_selected)
            
            row = i // 6
            col = i % 6
            color_grid.addWidget(btn, row, col)
            self.color_group.addButton(btn, i)
            
        layout.addLayout(color_grid)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.input.setFocus()

    def _on_color_selected(self):
        btn = self.sender()
        self.selected_color = btn.property("color_val")
        # Update borders to show selection
        for b in self.color_group.buttons():
            c = b.property("color_val")
            if b == btn:
                b.setStyleSheet(f"background-color: {c}; border: 2px solid white; border-radius: 3px;")
            else:
                b.setStyleSheet(f"background-color: {c}; border: 1px solid #808080; border-radius: 3px;")

    def format_time(self, seconds):
        if seconds is None: seconds = 0
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def get_data(self):
        return self.input.text().strip(), self.selected_color

    def get_label(self):
        return self.input.text().strip()
