import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QFrame,
    QSlider, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QIcon

from translator import tr

ROOT_DIR = Path(__file__).parent
RESOURCES_DIR = ROOT_DIR / "resources"

class VolumePopup(QWidget):
    """Popup window with audio track selection and volume slider."""
    audioChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)
        
        self.setObjectName("volumePopup")
        self.setMinimumWidth(330)
        
        # Left side: audio track list
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(4)
        
        list_lbl = QLabel(tr('player.tooltip_audio_track'))
        list_lbl.setStyleSheet("color: #aaa; font-size: 10px;")
        list_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_title_label = list_lbl
        self.list_layout.addWidget(list_lbl)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("audioList")
        self.list_widget.setFixedWidth(250)
        self.list_widget.setMaximumHeight(150)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_layout.addWidget(self.list_widget)

        
        main_layout.addLayout(self.list_layout)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #555;")
        main_layout.addWidget(sep)
        
        # Right side: volume slider
        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(4)
        slider_layout.setContentsMargins(5, 0, 5, 0)
        
        self.label = QLabel("100%")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #eaeaea; font-size: 12px;")
        slider_layout.addWidget(self.label)
        
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setObjectName("volumeSlider")
        self.slider.setRange(0, 200) # Max volume 200%
        self.slider.setMinimumHeight(80)
        self.slider.setFixedWidth(20)
        self.slider.valueChanged.connect(self._update_label)
        slider_layout.addWidget(self.slider, 0, Qt.AlignmentFlag.AlignHCenter)


        
        main_layout.addLayout(slider_layout)
        
        self.selected_index = -1
        self.items_data = []  # [(track_id, label), ...]
        
        # Initial style setup
        self._update_label(self.slider.value())

    def clearAudio(self):
        self.list_widget.clear()
        self.items_data = []
        self.selected_index = -1
    
    def addAudioItem(self, label, track_id):
        self.items_data.append((track_id, label))
        self.list_widget.addItem(label)
    
    def setAudioIndex(self, index):
        self.selected_index = index
        self._update_checkmarks()
    
    def audioItemData(self, index):
        if 0 <= index < len(self.items_data):
            return self.items_data[index][0]
        return None
    
    def audioCount(self):
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
        self.audioChanged.emit(index)
        # Auto-close after short timeout for visual feedback
        QTimer.singleShot(150, self.hide)

    def _update_label(self, value):
        self.label.setText(f"{value}%")
        
        # Dynamic color only for active part (add-page)
        if value <= 100:
            groove_color = "#018574" # Teal
        elif value <= 150:
            groove_color = "#cd950c" # Yellow / Gold
        else:
            groove_color = "#d32f2f" # Red
            
        # Handle always remains teal
        handle_color = "#018574"
        handle_hover = "#02a58a"
        handle_pressed = "#00634d"
            
        self.setStyleSheet(f"""
            QWidget#volumePopup {{
                background-color: #444444;
                border: 1px solid #555;
                border-radius: 3px;
            }}
            QSlider::groove:vertical {{
                background: #808080;
                width: 11px;
            }}
            QSlider::handle:vertical {{
                background: {handle_color};
                width: 16px;
                height: 16px;
                margin: 0 -4px;
                border: 2px solid #373737;
            }}
            QSlider::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QSlider::handle:vertical:pressed {{
                background: {handle_pressed};
            }}
            QSlider::sub-page:vertical {{
                background: #808080;
            }}
            QSlider::add-page:vertical {{
                background: {groove_color};
            }}
            QListWidget#audioList {{
                background-color: #3a3a3a;
                border: none;
                outline: none;
            }}
            QListWidget#audioList::item {{
                padding: 6px 10px;
                color: #eaeaea;
                border-bottom: 1px solid #484848;
            }}
            QListWidget#audioList::item:hover {{
                background-color: #505050;
            }}
            QListWidget#audioList::item:selected {{
                background-color: #018574;
            }}
            QLabel {{
                border: none;
                color: #aaa;
            }}
        """)

    def hideEvent(self, event):
        # Notify parent button when closed
        if isinstance(self.parent(), VolumeButton):
            self.parent().on_popup_hidden()
        super().hideEvent(event)

    def update_texts(self):
        """Update texts on language change."""
        self.audio_title_label.setText(tr('player.tooltip_audio_track'))
        self._update_label(self.slider.value())

class VolumeButton(QPushButton):
    """Volume button with popup slider and audio selection."""
    volumeChanged = pyqtSignal(int)
    audioChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        
        self.icons = {}
        for name in ["volume_mute", "volume_low", "volume_medium", "volume_hight"]:
            path = RESOURCES_DIR / "icons" / f"{name}.png"
            if path.exists():
                self.icons[name] = QIcon(str(path))
            else:
                self.icons[name] = QIcon()

        self.setIcon(self.icons['volume_hight'])
        self.setToolTip(tr('player.tooltip_volume'))
        self.popup = VolumePopup(self)
        self.popup.slider.valueChanged.connect(self._on_slider_changed)
        self.popup.audioChanged.connect(self.audioChanged.emit)
        self.popup.slider.setValue(100) # Initialize UI to match default volume
        self.last_hide_time = 0
        self.stored_volume = 20  # For restore after mute
        
    def on_popup_hidden(self):
        self.last_hide_time = time.time()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_popup()
        elif event.button() == Qt.MouseButton.RightButton:
            # Toggle mute
            current_volume = self.popup.slider.value()
            if current_volume > 0:
                self.stored_volume = current_volume
                self.popup.slider.setValue(0)
            else:
                restore = self.stored_volume if self.stored_volume > 0 else 20
                self.popup.slider.setValue(restore)
        else:
            super().mousePressEvent(event)

    def show_popup(self):
        # If window just closed (e.g. by clicking same button),
        # ignore immediate open attempt
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
        
    def _on_slider_changed(self, value):
        self._update_icon(value)
        self.volumeChanged.emit(value)
        
    def _update_icon(self, value):
        if value == 0:
            self.setIcon(self.icons['volume_mute'])
        elif value < 33:
            self.setIcon(self.icons['volume_low'])
        elif value < 66:
            self.setIcon(self.icons['volume_medium'])
        else:
            self.setIcon(self.icons['volume_hight'])
            
    def update_texts(self):
        self.setToolTip(tr('player.tooltip_volume'))
        self.popup.update_texts()
            
    def wheelEvent(self, event):
        # Allow changing volume with scroll on the button
        delta = event.angleDelta().y()
        step = 5 if delta > 0 else -5
        new_value = max(0, min(200, self.popup.slider.value() + step))
        self.popup.slider.setValue(new_value)
