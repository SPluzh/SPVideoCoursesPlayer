import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QPushButton,
    QFrame, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QIcon

from translator import tr

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

class SubtitlePopup(QWidget):
    """Popup window with subtitle list and settings."""
    subtitleChanged = pyqtSignal(int)
    styleChanged = pyqtSignal(str, object)  # (property_name, value)
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        main_layout = QHBoxLayout(self)  # Horizontal main layout
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        self.setObjectName("subtitlePopup")
        self.setMinimumWidth(380)
        
        # Left side: subtitle list
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("subtitleList")
        self.list_widget.setMinimumWidth(250)
        self.list_widget.setMaximumHeight(150)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        main_layout.addWidget(self.list_widget)

        
        # Right side: buttons and colors
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        right_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Size buttons (horizontal)
        size_layout = QVBoxLayout()
        size_layout.setSpacing(4)
        
        self.size_title_label = QLabel(tr('player.subtitle_size'))
        self.size_title_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.size_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_layout.addWidget(self.size_title_label)
        
        size_btns = QHBoxLayout()
        size_btns.setSpacing(4)
        self.size_down_btn = QPushButton("−")
        self.size_down_btn.setFixedSize(28, 28)
        self.size_down_btn.clicked.connect(self._decrease_size)
        self.size_up_btn = QPushButton("+")
        self.size_up_btn.setFixedSize(28, 28)
        self.size_up_btn.clicked.connect(self._increase_size)
        size_btns.addWidget(self.size_down_btn)
        size_btns.addWidget(self.size_up_btn)
        size_layout.addLayout(size_btns)
        right_panel.addLayout(size_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #555;")
        right_panel.addWidget(separator)
        
        # Text color
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.text_title_label = QLabel(tr('player.subtitle_text'))
        self.text_title_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.text_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(60, 22)
        self.text_color_btn.setStyleSheet("background-color: #FFFFFF; border: 1px solid #666;")
        self.text_color_btn.clicked.connect(self._pick_text_color)
        self.text_color = "#FFFFFF"
        text_layout.addWidget(self.text_title_label)
        text_layout.addWidget(self.text_color_btn)
        right_panel.addLayout(text_layout)
        
        # Outline color
        outline_layout = QVBoxLayout()
        outline_layout.setSpacing(2)
        self.outline_title_label = QLabel(tr('player.subtitle_outline'))
        self.outline_title_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.outline_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.outline_color_btn = QPushButton()
        self.outline_color_btn.setFixedSize(60, 22)
        self.outline_color_btn.setStyleSheet("background-color: #000000; border: 1px solid #666;")
        self.outline_color_btn.clicked.connect(self._pick_outline_color)
        self.outline_color = "#000000"
        outline_layout.addWidget(self.outline_title_label)
        outline_layout.addWidget(self.outline_color_btn)
        right_panel.addLayout(outline_layout)
        
        right_panel.addStretch()
        main_layout.addLayout(right_panel)
        
        self.selected_index = -1
        self.items_data = []  # [(track_id, label), ...]
        
        self.setStyleSheet("""
            QWidget#subtitlePopup {
                background-color: #444444;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QListWidget#subtitleList {
                background-color: #3a3a3a;
                border: none;
                outline: none;
            }
            QListWidget#subtitleList::item {
                padding: 6px 10px;
                color: #eaeaea;
                border-bottom: 1px solid #484848;
            }
            QListWidget#subtitleList::item:hover {
                background-color: #505050;
            }
            QListWidget#subtitleList::item:selected {
                background-color: #018574;
            }
            QPushButton {
                background-color: #555;
                color: #eaeaea;
                border: 1px solid #666;
                font-size: 14px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            QLabel {
                color: #aaa;
                border: none;
            }
        """)
        
        # Bright colors for text (with teal)
        self.text_colors = [
            "#FFFFFF", "#FFFF00", "#00FF00", "#00FFFF", 
            "#FF00FF", "#FF0000", "#FFA500", "#018574",
            "#FFD700", "#7FFF00", "#FF69B4", "#00BFFF"
        ]
        
        # Dark colors for outline
        self.outline_colors = [
            "#000000", "#1a1a1a", "#333333", "#4d4d4d",
            "#0d0d0d", "#262626", "#404040", "#595959",
            "#1c1c1c", "#2e2e2e", "#424242", "#555555"
        ]

    
    def _show_color_palette(self, target_btn, current_color, signal_name, colors):
        """Show mini color palette."""
        palette = QWidget(self, Qt.WindowType.Popup)
        palette.setStyleSheet("background-color: #444; border: 1px solid #555; padding: 5px; border-radius: 3px;")
        layout = QGridLayout(palette)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        cols = 4  # 4 colors per row
        for i, color in enumerate(colors):
            row = i // cols
            col = i % cols
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #666; border-radius: 3px;")
            btn.clicked.connect(lambda checked, c=color: self._apply_color(c, target_btn, signal_name, palette))
            layout.addWidget(btn, row, col)
        
        palette.adjustSize()
        pos = target_btn.mapToGlobal(QPoint(0, target_btn.height() + 5))
        
        target_x = pos.x()
        target_y = pos.y()
        
        # Screen boundary check
        screen = self.screen().availableGeometry()
        target_x = max(screen.left(), min(target_x, screen.right() - palette.width()))
        target_y = max(screen.top(), min(target_y, screen.bottom() - palette.height()))
        
        palette.move(target_x, target_y)
        palette.show()
    
    def _apply_color(self, color, target_btn, signal_name, palette):
        """Apply selected color."""
        target_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #666; border-radius: 3px;")
        if signal_name == "sub-color":
            self.text_color = color
        else:
            self.outline_color = color
        self.styleChanged.emit(signal_name, color)
        palette.close()
    
    def _pick_text_color(self):
        self._show_color_palette(self.text_color_btn, self.text_color, "sub-color", self.text_colors)
    
    def _pick_outline_color(self):
        self._show_color_palette(self.outline_color_btn, self.outline_color, "sub-border-color", self.outline_colors)

    
    def _increase_size(self):
        self.styleChanged.emit("sub-scale", 5)  # increase by 5%
    
    def _decrease_size(self):
        self.styleChanged.emit("sub-scale", -5)  # decrease by 5%
    
    def clear(self):
        self.list_widget.clear()
        self.items_data = []
        self.selected_index = -1
    
    def addItem(self, label, track_id):
        self.items_data.append((track_id, label))
        self.list_widget.addItem(label)
    
    def setCurrentIndex(self, index):
        self.selected_index = index
        self._update_checkmarks()
    
    def itemData(self, index):
        if 0 <= index < len(self.items_data):
            return self.items_data[index][0]
        return None
    
    def count(self):
        return len(self.items_data)
    
    def _update_checkmarks(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if i < len(self.items_data):
                _, label = self.items_data[i]
                if i == self.selected_index:
                    item.setText(f"✓ {label}")
                else:
                    item.setText(f"   {label}")
    
    def _on_item_clicked(self, item):
        index = self.list_widget.row(item)
        self.selected_index = index
        self._update_checkmarks()
        self.subtitleChanged.emit(index)
        # Close popup after selection
        QTimer.singleShot(150, self.hide)
    
    def hideEvent(self, event):
        if isinstance(self.parent(), SubtitleButton):
            self.parent().on_popup_hidden()
        super().hideEvent(event)

    def update_texts(self):
        """Update texts on language change."""
        self.size_title_label.setText(tr('player.subtitle_size'))
        self.text_title_label.setText(tr('player.subtitle_text'))
        self.outline_title_label.setText(tr('player.subtitle_outline'))


class SubtitleButton(QPushButton):
    """Subtitle button: Left click - select, Right click - toggle on/off."""
    subtitleToggled = pyqtSignal(bool)  # True = on, False = off
    subtitleChanged = pyqtSignal(int)  # combo box index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(30)
        
        self.icons = {}
        for name in ["subtitle_on", "subtitle_off"]:
            path = RESOURCES_DIR / "icons" / f"{name}.png"
            if path.exists():
                self.icons[name] = QIcon(str(path))
            else:
                self.icons[name] = QIcon()

        self.setToolTip(tr('player.tooltip_subtitle_track'))
        self.popup = SubtitlePopup(self)
        self.popup.subtitleChanged.connect(self._on_subtitle_changed)
        self.last_hide_time = 0
        self.subtitles_enabled = False
        self._update_icon()
    
    def on_popup_hidden(self):
        self.last_hide_time = time.time()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Left click - show selection popup
            self.show_popup()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click - toggle subtitles on/off
            self.subtitles_enabled = not self.subtitles_enabled
            self._update_icon()
            self.subtitleToggled.emit(self.subtitles_enabled)
        else:
            super().mousePressEvent(event)
    
    def show_popup(self):
        if time.time() - self.last_hide_time < 0.2:
            return
            
        if self.popup.isVisible():
            self.popup.hide()
            return
            
        # Position popup above the button
        self.popup.adjustSize()
        pos = self.mapToGlobal(QPoint(0, 0))
        
        target_x = pos.x() + (self.width() - self.popup.width()) // 2
        target_y = pos.y() - self.popup.height() - 5
        
        # Screen boundary check
        screen = self.screen().availableGeometry()
        target_x = max(screen.left(), min(target_x, screen.right() - self.popup.width()))
        target_y = max(screen.top(), min(target_y, screen.bottom() - self.popup.height()))
        
        self.popup.move(target_x, target_y)
        self.popup.show()
    
    def _on_subtitle_changed(self, index):
        self.subtitleChanged.emit(index)
        # Automatically enable subtitles upon selection
        self.subtitles_enabled = True
        self._update_icon()
    
    def _update_icon(self):
        if self.subtitles_enabled:
            self.setIcon(self.icons['subtitle_on'])
        else:
            self.setIcon(self.icons['subtitle_off'])
    
    def set_enabled_state(self, enabled):
        """Set enabled state (for synchronization with combo)."""
        self.subtitles_enabled = enabled
        self._update_icon()

    def update_texts(self):
        """Update texts on language change."""
        self.setToolTip(tr('player.tooltip_subtitle_track'))
        self.popup.update_texts()

