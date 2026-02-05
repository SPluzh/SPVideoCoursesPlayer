from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QColor, QPalette

from translator import tr

class MarkerItem(QFrame):
    """A single item in the marker gallery."""
    clicked = pyqtSignal(float) # timestamp
    delete_requested = pyqtSignal(int) # marker_id
    edit_requested = pyqtSignal(dict) # marker_data

    def __init__(self, marker_data, parent=None):
        super().__init__(parent)
        self.marker_data = marker_data
        self.marker_id = marker_data.get('id')
        self.timestamp = marker_data.get('position_seconds', 0)
        self.label_text = marker_data.get('label', "")
        self.color = marker_data.get('color', "#FFD700")
        
        self.setFixedSize(180, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(170, 96) # 16:9 approx
        self.thumb_label.setStyleSheet("background-color: #000000; border: 1px solid rgba(255, 255, 255, 30); border-radius: 4px;")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("...")
        layout.addWidget(self.thumb_label)

        # Time Label with plate (Overlay on thumbnail)
        m, s = divmod(int(self.timestamp), 60)
        h, m = divmod(m, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        
        self.time_label = QLabel(time_str, self.thumb_label)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: #ffffff;
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        
        # Position time_label at the bottom right of thumb_label
        thumb_layout = QVBoxLayout(self.thumb_label)
        thumb_layout.setContentsMargins(0, 0, 4, 4) # Small margin from edges
        thumb_layout.addStretch()
        time_hbox = QHBoxLayout()
        time_hbox.addStretch()
        time_hbox.addWidget(self.time_label)
        thumb_layout.addLayout(time_hbox)
        
        # Title Label with plate
        self.title_label = QLabel(self.label_text)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 200);
            color: #eaeaea;
            border: 1px solid {self.color};
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
        """)
        self.title_label.setWordWrap(False)
        layout.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignCenter)

        
        self.setStyleSheet(f"""
            MarkerItem {{
                background-color: rgba(42, 42, 42, 180);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 30);
            }}
            MarkerItem:hover {{
                background-color: rgba(60, 60, 60, 220);
                border: 1px solid rgba(255, 255, 255, 80);
            }}
        """)

    def set_pixmap(self, pixmap):
        scaled = pixmap.scaled(self.thumb_label.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setText("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.timestamp)

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        edit_action = context_menu.addAction(tr('player.edit_marker') or "Edit Marker")
        delete_action = context_menu.addAction(tr('player.delete_marker') or "Delete Marker")

        action = context_menu.exec(event.globalPos())

        if action == edit_action:
            self.edit_requested.emit(self.marker_data)
        elif action == delete_action:
            self.delete_requested.emit(self.marker_id)

class MarkerGalleryWidget(QFrame):
    """Horizontal gallery of markers with screenshots."""
    seek_requested = pyqtSignal(float)
    delete_requested = pyqtSignal(int) # marker_id
    edit_requested = pyqtSignal(dict) # marker_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(180)
        self.setStyleSheet("""
            MarkerGalleryWidget {
                background-color: rgba(10, 10, 10, 150);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch() # Initial stretch
        
        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)
        
        self.items = {} # {marker_id: MarkerItem}

    def set_markers(self, markers):
        """Update the gallery with a list of markers."""
        # Clear existing
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        self.items.clear()
        
        # Sort markers by time
        sorted_markers = sorted(markers, key=lambda x: x.get('position_seconds', 0))
        
        for m in sorted_markers:
            item = MarkerItem(m)
            item.clicked.connect(self.seek_requested)
            item.edit_requested.connect(self.edit_requested)
            item.delete_requested.connect(self.delete_requested)
            self.content_layout.insertWidget(self.content_layout.count() - 1, item)
            self.items[m['id']] = item
            
        if not sorted_markers:
            lbl = QLabel(tr('player.no_markers') or "No markers found")
            lbl.setStyleSheet("""
                background-color: rgba(0, 0, 0, 100);
                color: #aaaaaa;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 20);
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Center the label in the layout
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.addStretch()
            vbox.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            vbox.addStretch()
            self.content_layout.insertWidget(0, container)

    def update_thumbnail(self, marker_id, pixmap):
        """Update thumbnail for a specific marker."""
        if marker_id in self.items:
            self.items[marker_id].set_pixmap(pixmap)
        # Also check if it's a timestamp-based ID (for new markers)
        elif f"ts_{marker_id}" in self.items:
             self.items[f"ts_{marker_id}"].set_pixmap(pixmap)

