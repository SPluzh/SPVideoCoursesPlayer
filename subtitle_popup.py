import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QLabel, QPushButton,
    QFrame, QGridLayout, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect
from PyQt6.QtGui import QIcon

from translator import tr

from constants import RESOURCES_DIR
from icon_manager import load_icons_dict

class SubtitlePopup(QWidget):
    """Popup window with subtitle list and settings."""
    subtitleChanged = pyqtSignal(int)
    styleChanged = pyqtSignal(str, object)  # (property_name, value)
    subtitleToggled = pyqtSignal(bool)
    interactiveToggled = pyqtSignal(bool)
    secondarySubtitleToggled = pyqtSignal(bool)
    secondarySubtitleChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        
        main_layout = QHBoxLayout(self)  # Horizontal main layout
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        self.setObjectName("subtitlePopup")
        self.setMinimumWidth(380)
        self.setFixedHeight(270)
        
        # Left side: toggle + subtitle list
        left_panel = QHBoxLayout()
        left_panel.setSpacing(8)
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Toggle button column
        toggle_col = QVBoxLayout()
        toggle_col.setContentsMargins(0, 0, 0, 0)
        toggle_col.setSpacing(0)
        
        # Spacer to align with list (to offset the list label height)
        toggle_col.addSpacing(16) 
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.clicked.connect(self._toggle_subtitles)
        self.toggle_btn.setObjectName("popupSubtitleToggle")
        toggle_col.addWidget(self.toggle_btn)
        
        toggle_col.addSpacing(6)
        
        self.interactive_btn = QPushButton()
        self.interactive_btn.setFixedSize(30, 30)
        self.interactive_btn.setCheckable(True)
        self.interactive_btn.setObjectName("interactiveSubtitlesBtn")
        self.interactive_btn.setToolTip(tr('player.interactive_subtitles'))
        self.interactive_btn.toggled.connect(self._on_interactive_toggled)
        toggle_col.addWidget(self.interactive_btn)
        
        toggle_col.addStretch()
        left_panel.addLayout(toggle_col)

        # List section (vertical: label + list)
        list_section = QVBoxLayout()
        list_section.setSpacing(4)
        list_section.setContentsMargins(0, 0, 0, 0)
        
        self.list_title_label = QLabel(tr('player.subtitle_tracks'))
        self.list_title_label.setObjectName("popupHeaderLabel")
        # Removing fixed height to allow QSS control
        list_section.addWidget(self.list_title_label)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("subtitleList")
        self.list_widget.setMinimumWidth(250)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        list_section.addWidget(self.list_widget)
        
        # Separator (Horizontal)
        sep_h = QFrame()
        sep_h.setObjectName("aboutSeparator")
        sep_h.setFrameShape(QFrame.Shape.HLine)
        list_section.addWidget(sep_h)

        # Enable checkbox
        self.secondary_enabled_cb = QCheckBox(tr("player.enable_secondary_subtitle"))
        self.secondary_enabled_cb.setObjectName("secondarySubtitleCheckbox")
        self.secondary_enabled_cb.toggled.connect(self._on_secondary_enabled_toggled)
        list_section.addWidget(self.secondary_enabled_cb)

        # Container for secondary controls
        self.secondary_container = QWidget()
        sec_layout = QVBoxLayout(self.secondary_container)
        sec_layout.setContentsMargins(0, 0, 0, 0)
        sec_layout.setSpacing(4)

        self.secondary_title_label = QLabel(tr("player.secondary_subtitle_track"))
        self.secondary_title_label.setObjectName("popupHeaderLabel")
        sec_layout.addWidget(self.secondary_title_label)

        self.secondary_list_widget = QListWidget()
        self.secondary_list_widget.setObjectName("subtitleList")
        self.secondary_list_widget.setMinimumWidth(250)
        self.secondary_list_widget.setFixedHeight(80)
        self.secondary_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.secondary_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.secondary_list_widget.itemClicked.connect(self._on_secondary_item_clicked)
        sec_layout.addWidget(self.secondary_list_widget)

        # Initially hide the container
        self.secondary_container.setVisible(False)
        list_section.addWidget(self.secondary_container)
        
        left_panel.addLayout(list_section)
        
        main_layout.addLayout(left_panel)
        
        # Load icons
        self.icons = load_icons_dict(["subtitle_on", "subtitle_off", "languages"])
        self.interactive_btn.setIcon(self.icons["languages"])
        
        self.subtitles_enabled = False
        self._update_toggle_icon()

        
        # Right side: buttons and colors
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Size buttons (horizontal)
        size_layout = QVBoxLayout()
        size_layout.setSpacing(4)
        
        self.size_title_label = QLabel(tr('player.subtitle_size'))
        self.size_title_label.setObjectName("popupHeaderLabel")
        size_layout.addWidget(self.size_title_label)
        
        size_btns = QHBoxLayout()
        size_btns.setSpacing(4)
        self.size_down_btn = QPushButton("−")
        self.size_down_btn.setFixedSize(30, 30)
        self.size_down_btn.clicked.connect(self._decrease_size)
        self.size_up_btn = QPushButton("+")
        self.size_up_btn.setFixedSize(30, 30)
        self.size_up_btn.clicked.connect(self._increase_size)
        size_btns.addWidget(self.size_down_btn)
        size_btns.addWidget(self.size_up_btn)
        size_layout.addLayout(size_btns)
        right_panel.addLayout(size_layout)
        
        # Text color
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.text_title_label = QLabel(tr('player.subtitle_text'))
        self.text_title_label.setObjectName("popupHeaderLabel")
        self.text_title_label.setContentsMargins(0, 0, 0, 0)
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(64, 30)
        self.text_color_btn.setObjectName("textColorBtn")
        self.text_color_btn.clicked.connect(self._pick_text_color)
        self.text_color = "#FFFFFF"
        self._update_text_color_btn()
        text_layout.addWidget(self.text_title_label)
        text_layout.addWidget(self.text_color_btn)
        right_panel.addLayout(text_layout)

        # Secondary text color
        secondary_text_layout = QVBoxLayout()
        secondary_text_layout.setSpacing(2)
        self.secondary_text_title_label = QLabel(tr('player.secondary_subtitle_text'))
        self.secondary_text_title_label.setObjectName("popupHeaderLabel")
        self.secondary_text_title_label.setContentsMargins(0, 0, 0, 0)
        self.secondary_text_color_btn = QPushButton()
        self.secondary_text_color_btn.setFixedSize(64, 30)
        self.secondary_text_color_btn.setObjectName("secondaryTextColorBtn")
        self.secondary_text_color_btn.clicked.connect(self._pick_secondary_text_color)
        self.secondary_text_color = "#ADD8E6"
        self._update_secondary_text_color_btn()
        secondary_text_layout.addWidget(self.secondary_text_title_label)
        secondary_text_layout.addWidget(self.secondary_text_color_btn)
        right_panel.addLayout(secondary_text_layout)
        
        # Outline color
        outline_layout = QVBoxLayout()
        outline_layout.setSpacing(2)
        self.outline_title_label = QLabel(tr('player.subtitle_outline'))
        self.outline_title_label.setObjectName("popupHeaderLabel")
        self.outline_title_label.setContentsMargins(0, 0, 0, 0)
        self.outline_color_btn = QPushButton()
        self.outline_color_btn.setFixedSize(64, 30)
        self.outline_color_btn.setObjectName("outlineColorBtn")
        self.outline_color_btn.clicked.connect(self._pick_outline_color)
        self.outline_color = "#000000"
        self._update_outline_color_btn()
        outline_layout.addWidget(self.outline_title_label)
        outline_layout.addWidget(self.outline_color_btn)
        right_panel.addLayout(outline_layout)
        
        right_panel.addStretch()
        main_layout.addLayout(right_panel)
        
        self.selected_index = -1
        self.items_data = []  # [(track_id, label), ...]
        self.secondary_selected_index = -1
        self.secondary_items_data = []  # [(track_id, label), ...]
        
        # Professional cinema text colors
        self.text_colors = [
            "#FFFFFF", "#FFFF00", "#FFD700", "#ADD8E6",
            "#90EE90", "#FFB6C1", "#E6E6FA", "#FFE4B5",
            "#AFEEEE", "#DCDCDC", "#FFA500", "#018574"
        ]
        
        # Dark colorful outline colors
        self.outline_colors = [
            "#000000", "#4D0000", "#003300", "#00004D",
            "#331A00", "#330033", "#003333", "#1A0033",
            "#2F4F4F", "#222222", "#424242", "#004D40"
        ]

    
    def _show_color_palette(self, target_btn, current_color, signal_name, colors):
        """Show mini color palette."""
        palette = QWidget(self, Qt.WindowType.Popup)
        palette.setObjectName("colorPalette")
        layout = QGridLayout(palette)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        cols = 4  # 4 colors per row
        for i, color in enumerate(colors):
            row = i // cols
            col = i % cols
            btn = QPushButton()
            btn.setFixedSize(33, 33)
            btn.setStyleSheet(f"background-color: {color};") # Keep background color in Python
            btn.clicked.connect(lambda checked, c=color: self._apply_color(c, target_btn, signal_name, palette))
            layout.addWidget(btn, row, col)
        
        palette.ensurePolished()
        palette.adjustSize()
        
        # Determine current screen based on button center
        btn_center_global = target_btn.mapToGlobal(target_btn.rect().center())
        screen = QApplication.screenAt(btn_center_global)
        if not screen:
            screen = self.window().screen() if self.window() else QApplication.primaryScreen()
            
        screen_geo = screen.availableGeometry()
        
        # Use the absolute maximum possible width/height for safest clamping
        pw = max(palette.width(), palette.sizeHint().width(), palette.minimumWidth())
        ph = max(palette.height(), palette.sizeHint().height(), palette.minimumHeight())
        
        btn_rect_global = QRect(target_btn.mapToGlobal(QPoint(0, 0)), target_btn.size())
        target_x = btn_rect_global.left()
        target_y = btn_rect_global.bottom() + 5
        
        # Clamp strictly within available geometry
        margin_x = 20
        margin_right = 30
        margin_top = 20
        
        min_x = screen_geo.left() + margin_x
        max_x = screen_geo.left() + screen_geo.width() - pw - margin_right
        min_y = screen_geo.top() + margin_top
        max_y = screen_geo.top() + screen_geo.height() - ph # No bottom margin
        
        target_x = max(min_x, min(target_x, max_x))
        target_y = max(min_y, min(target_y, max_y))
        
        palette.move(target_x, target_y)
        palette.show()
    
    def _apply_color(self, color, target_btn, signal_name, palette):
        """Apply selected color."""
        target_btn.setStyleSheet(f"background-color: {color};")
        if signal_name == "sub-color":
            self.text_color = color
        elif signal_name == "sub-secondary-color":
            self.secondary_text_color = color
        else:
            self.outline_color = color
        self.styleChanged.emit(signal_name, color)
        palette.close()
    
    def _pick_text_color(self):
        self._show_color_palette(self.text_color_btn, self.text_color, "sub-color", self.text_colors)
    
    def _pick_secondary_text_color(self):
        self._show_color_palette(self.secondary_text_color_btn, self.secondary_text_color, "sub-secondary-color", self.text_colors)
    
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
    
    def _toggle_subtitles(self):
        self.subtitles_enabled = not self.subtitles_enabled
        self._update_toggle_icon()
        self.subtitleToggled.emit(self.subtitles_enabled)
        
    def _update_toggle_icon(self):
        icon_name = "subtitle_on" if self.subtitles_enabled else "subtitle_off"
        self.toggle_btn.setIcon(self.icons[icon_name])
        
    def setSubtitlesEnabled(self, enabled):
        self.subtitles_enabled = enabled
        self._update_toggle_icon()
    
    def hideEvent(self, event):
        if isinstance(self.parent(), SubtitleButton):
            self.parent().on_popup_hidden()
        super().hideEvent(event)

    def _update_text_color_btn(self):
        self.text_color_btn.setStyleSheet(f"background-color: {self.text_color};")

    def _update_secondary_text_color_btn(self):
        if hasattr(self, "secondary_text_color_btn"):
            self.secondary_text_color_btn.setStyleSheet(f"background-color: {self.secondary_text_color};")

    def _update_outline_color_btn(self):
        self.outline_color_btn.setStyleSheet(f"background-color: {self.outline_color};")

    def _on_interactive_toggled(self, checked):
        self.interactiveToggled.emit(checked)

    def setInteractiveSubtitlesEnabled(self, enabled):
        self.interactive_btn.blockSignals(True)
        self.interactive_btn.setChecked(enabled)
        self.interactive_btn.blockSignals(False)

    def update_texts(self):
        """Update texts on language change."""
        self.list_title_label.setText(tr('player.subtitle_tracks'))
        self.size_title_label.setText(tr('player.subtitle_size'))
        self.text_title_label.setText(tr('player.subtitle_text'))
        if hasattr(self, 'secondary_text_title_label'):
            self.secondary_text_title_label.setText(tr('player.secondary_subtitle_text'))
        self.outline_title_label.setText(tr('player.subtitle_outline'))
        self.interactive_btn.setToolTip(tr('player.interactive_subtitles'))
        self.secondary_enabled_cb.setText(tr('player.enable_secondary_subtitle'))
        self.secondary_title_label.setText(tr('player.secondary_subtitle_track'))
        self._update_checkmarks()
        self._update_secondary_checkmarks()

    def _on_secondary_enabled_toggled(self, checked):
        self.secondary_container.setVisible(checked)
        if checked and self.secondary_selected_index == -1 and len(self.secondary_items_data) > 0:
            idx = 0
            if len(self.secondary_items_data) > 1:
                if self.selected_index == 0:
                    idx = 1
                else:
                    idx = 0
            self.secondary_selected_index = idx
            self._update_secondary_checkmarks()
            track_id = self.secondary_items_data[idx][0]
            self.secondarySubtitleChanged.emit(track_id)
        self.secondarySubtitleToggled.emit(checked)

    def _on_secondary_item_clicked(self, item):
        index = self.secondary_list_widget.row(item)
        self.secondary_selected_index = index
        self._update_secondary_checkmarks()
        if 0 <= index < len(self.secondary_items_data):
            track_id = self.secondary_items_data[index][0]
            self.secondarySubtitleChanged.emit(track_id)
        if not self.secondary_enabled_cb.isChecked():
            self.secondary_enabled_cb.blockSignals(True)
            self.secondary_enabled_cb.setChecked(True)
            self.secondary_enabled_cb.blockSignals(False)
            self.secondary_container.setVisible(True)
            self.secondarySubtitleToggled.emit(True)
        QTimer.singleShot(150, self.hide)

    def clearSecondary(self):
        self.secondary_list_widget.clear()
        self.secondary_items_data = []
        self.secondary_selected_index = -1

    def addSecondaryItem(self, label, track_id):
        self.secondary_items_data.append((track_id, label))
        self.secondary_list_widget.addItem(label)

    def setSecondaryIndex(self, index):
        self.secondary_selected_index = index
        self._update_secondary_checkmarks()

    def secondaryItemData(self, index):
        if 0 <= index < len(self.secondary_items_data):
            return self.secondary_items_data[index][0]
        return None

    def _update_secondary_checkmarks(self):
        for i in range(self.secondary_list_widget.count()):
            item = self.secondary_list_widget.item(i)
            if i < len(self.secondary_items_data):
                _, label = self.secondary_items_data[i]
                if i == self.secondary_selected_index:
                    item.setText(f"✓ {label}")
                else:
                    item.setText(f"   {label}")

    def setSecondaryEnabled(self, enabled):
        self.secondary_enabled_cb.blockSignals(True)
        self.secondary_enabled_cb.setChecked(enabled)
        self.secondary_enabled_cb.blockSignals(False)
        self.secondary_container.setVisible(enabled)


class SubtitleButton(QPushButton):
    """Subtitle button: Left click - select, Right click - toggle on/off."""
    subtitleToggled = pyqtSignal(bool)  # True = on, False = off
    subtitleChanged = pyqtSignal(int)  # combo box index
    secondarySubtitleToggled = pyqtSignal(bool)
    secondarySubtitleChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        
        self.icons = load_icons_dict(["subtitle_on", "subtitle_off"])

        self.setToolTip(tr('player.tooltip_subtitle_track'))
        self.popup = SubtitlePopup(self)
        self.popup.subtitleChanged.connect(self._on_subtitle_changed)
        self.popup.subtitleToggled.connect(self._on_popup_subtitle_toggled)
        self.popup.secondarySubtitleToggled.connect(self.secondarySubtitleToggled.emit)
        self.popup.secondarySubtitleChanged.connect(self.secondarySubtitleChanged.emit)
        self.last_hide_time = 0
        self.subtitles_enabled = False
        self._update_icon()
    
    def on_popup_hidden(self):
        self.last_hide_time = time.time()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Left click - toggle subtitles on/off
            self.subtitles_enabled = not self.subtitles_enabled
            self._update_icon()
            self.subtitleToggled.emit(self.subtitles_enabled)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click - show selection popup
            self.show_popup()
        else:
            super().mousePressEvent(event)
    
    def show_popup(self):
        if time.time() - self.last_hide_time < 0.2:
            return
            
        if self.popup.isVisible():
            self.popup.hide()
            return
            
        # Position popup above the button
        self.popup.setSubtitlesEnabled(self.subtitles_enabled)
        self.popup._update_checkmarks()  # Ensure checkmarks are up-to-date
        self.popup._update_secondary_checkmarks()
        self.popup.ensurePolished()
        self.popup.adjustSize()
        
        # Determine current screen based on button center
        button_rect_global = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
        button_center_global = button_rect_global.center()
        
        screen = QApplication.screenAt(button_center_global)
        if not screen:
            screen = self.window().screen() if self.window() else QApplication.primaryScreen()
        
        screen_geo = screen.availableGeometry()
        
        # Use adjusted size directly
        pw = self.popup.width()
        ph = self.popup.height()
        
        # Calculate ideal target (above button)
        target_x = button_center_global.x() - pw // 2
        target_y = button_rect_global.top() - ph - 5
        
        # Clamp strictly within available geometry
        margin_x = 20
        margin_right = 30
        margin_top = 20
        
        min_x = screen_geo.left() + margin_x
        max_x = screen_geo.left() + screen_geo.width() - pw - margin_right
        min_y = screen_geo.top() + margin_top
        max_y = screen_geo.top() + screen_geo.height() - ph # No bottom margin
        
        target_x = max(min_x, min(target_x, max_x))
        target_y = max(min_y, min(target_y, max_y))
        
        self.popup.move(target_x, target_y)
        self.popup.show()

    def _on_popup_subtitle_toggled(self, enabled):
        self.subtitles_enabled = enabled
        self._update_icon()
        self.subtitleToggled.emit(enabled)
    
    def _on_subtitle_changed(self, index):
        self.subtitleChanged.emit(index)
        # Automatically enable subtitles upon selection
        self.subtitles_enabled = True
        self.popup.setSubtitlesEnabled(True)
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

    def clearSecondary(self):
        self.popup.clearSecondary()

    def addSecondaryItem(self, label, track_id):
        self.popup.addSecondaryItem(label, track_id)

    def setSecondaryIndex(self, index):
        self.popup.setSecondaryIndex(index)

    def setSecondaryEnabled(self, enabled):
        self.popup.setSecondaryEnabled(enabled)

    def secondaryItemData(self, index):
        return self.popup.secondaryItemData(index)

