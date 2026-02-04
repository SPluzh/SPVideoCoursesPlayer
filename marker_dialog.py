from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QButtonGroup, QDialogButtonBox, QGridLayout
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from translator import tr

class MarkerDialog(QDialog):
    """Simple dialog to add/edit a marker."""
    def __init__(self, parent=None, timestamp=0.0, label="", color="#FFD700", max_duration=0.0):
        super().__init__(parent)
        print(f"DEBUG: MarkerDialog init, timestamp={timestamp}, max_duration={max_duration}") # DEBUG
        self.setWindowTitle(tr('player.add_marker_title'))
        self.setFixedWidth(350)
        self.selected_color = color
        self.max_duration = max_duration or 0.0
        
        layout = QVBoxLayout(self)
        
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(f"{tr('player.marker_timestamp')}:"))
        
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedWidth(30)
        self.btn_minus.setAutoRepeat(True)
        self.btn_minus.setAutoRepeatDelay(500)
        self.btn_minus.setAutoRepeatInterval(100)
        self.btn_minus.clicked.connect(lambda: self._adjust_time(-1))
        
        self.time_input = QLineEdit()
        self.time_input.setText(self.format_time(timestamp))
        self.time_input.setFixedWidth(80)
        
        # Restriction: Only allow digits and colons
        time_regex = QRegularExpression("^[0-9:]*$")
        self.time_input.setValidator(QRegularExpressionValidator(time_regex, self))
        
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedWidth(30)
        self.btn_plus.setAutoRepeat(True)
        self.btn_plus.setAutoRepeatDelay(500)
        self.btn_plus.setAutoRepeatInterval(100)
        self.btn_plus.clicked.connect(lambda: self._adjust_time(1))
        
        time_layout.addWidget(self.btn_minus)
        time_layout.addWidget(self.time_input)
        time_layout.addWidget(self.btn_plus)
        time_layout.addStretch()
        layout.addLayout(time_layout)
        
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

    def _adjust_time(self, delta):
        """Adjust timestamp by delta seconds."""
        current_sec = self.parse_time(self.time_input.text().strip())
        new_sec = current_sec + delta
        if self.max_duration > 0:
            new_sec = max(0, min(new_sec, self.max_duration))
        else:
            new_sec = max(0, new_sec)
        self.time_input.setText(self.format_time(new_sec))

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

    def parse_time(self, time_str):
        """Parse HH:MM:SS or MM:SS to seconds."""
        try:
            parts = [int(p) for p in time_str.split(':')]
            if len(parts) == 3: # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2: # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 1: # SS
                return parts[0]
        except:
            pass
        return 0

    def get_data(self):
        label = self.input.text().strip()
        color = self.selected_color
        pos = self.parse_time(self.time_input.text().strip())
        
        # Validation and capping
        if self.max_duration > 0:
            pos = max(0, min(pos, self.max_duration))
        else:
            pos = max(0, pos)
            
        return label, color, pos

    def get_label(self):
        return self.input.text().strip()
