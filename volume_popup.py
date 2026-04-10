import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QFrame,
    QSlider,
    QPushButton,
    QApplication,
    QTabWidget,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QButtonGroup,
    QRadioButton,
    QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect
from PyQt6.QtGui import QIcon

from translator import tr
from constants import RESOURCES_DIR
from icon_manager import load_icons_dict


class VolumePopup(QWidget):
    """Popup window for Tracks and Audio Tools (no tabs)."""

    # Signals
    volumeChanged = pyqtSignal(int)
    audioChanged = pyqtSignal(int)

    # DSP Signals
    noiseModeChanged = pyqtSignal(str)  # off, standard, ai
    compressorToggled = pyqtSignal(bool)
    deesserToggled = pyqtSignal(bool)
    channelModeChanged = pyqtSignal(str)  # normal, mono, swap
    delayChanged = pyqtSignal(float)  # seconds

    # Secondary Audio Signals
    secondaryAudioToggled = pyqtSignal(bool)
    secondaryAudioTrackChanged = pyqtSignal(int)  # track_id
    secondaryAudioVolumeChanged = pyqtSignal(int)  # 0-100

    def __init__(self, parent=None):
        super().__init__(
            parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setObjectName("volumePopup")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        # 1. Left: DSP Tools (Grid for buttons)
        dsp_main_layout = QVBoxLayout()
        dsp_main_layout.setSpacing(6)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.noise_btn = QPushButton(tr("player.audio_tools.noise"))
        self.noise_btn.setObjectName("audioFilterBtn")
        self.noise_btn.setToolTip(tr("player.audio_tools.noise_tooltip"))
        self.noise_btn.setFixedWidth(54)
        self.noise_btn.setFixedHeight(24)
        self.noise_btn.clicked.connect(self.cycle_noise_mode)
        grid_layout.addWidget(self.noise_btn, 0, 0)

        self.comp_btn = QPushButton(tr("player.audio_tools.comp"))
        self.comp_btn.setObjectName("audioFilterBtn")
        self.comp_btn.setCheckable(True)
        self.comp_btn.setToolTip(tr("player.audio_tools.comp_tooltip"))
        self.comp_btn.setFixedWidth(54)
        self.comp_btn.setFixedHeight(24)
        self.comp_btn.toggled.connect(self.compressorToggled.emit)
        grid_layout.addWidget(self.comp_btn, 0, 1)

        self.deess_btn = QPushButton(tr("player.audio_tools.deess"))
        self.deess_btn.setObjectName("audioFilterBtn")
        self.deess_btn.setCheckable(True)
        self.deess_btn.setToolTip(tr("player.audio_tools.deess_tooltip"))
        self.deess_btn.setFixedWidth(54)
        self.deess_btn.setFixedHeight(24)
        self.deess_btn.toggled.connect(self.deesserToggled.emit)
        grid_layout.addWidget(self.deess_btn, 1, 0)

        self.mono_btn = QPushButton(tr("player.audio_tools.mono"))
        self.mono_btn.setObjectName("audioFilterBtn")
        self.mono_btn.setCheckable(True)
        self.mono_btn.setToolTip(tr("player.audio_tools.mono_tooltip"))
        self.mono_btn.setFixedWidth(54)
        self.mono_btn.setFixedHeight(24)
        self.mono_btn.toggled.connect(self._on_mono_toggled)
        grid_layout.addWidget(self.mono_btn, 1, 1)

        dsp_main_layout.addLayout(grid_layout)

        # Audio Delay Control
        dsp_main_layout.addSpacing(4)
        self.delay_lbl = QLabel(tr("player.audio_delay"))
        self.delay_lbl.setObjectName("popupHeaderLabel")
        # Removed manual stylesheet
        dsp_main_layout.addWidget(self.delay_lbl)

        delay_row = QHBoxLayout()
        delay_row.setSpacing(1)
        delay_row.setContentsMargins(0, 0, 0, 0)

        self.delay_minus = QPushButton("-")
        self.delay_minus.setFixedSize(24, 24)
        self.delay_minus.setObjectName("delaySmallBtn")
        self.delay_minus.setAutoRepeat(True)
        self.delay_minus.setAutoRepeatDelay(300)
        self.delay_minus.setAutoRepeatInterval(50)
        self.delay_minus.clicked.connect(lambda: self.adjust_delay(-50))
        delay_row.addWidget(self.delay_minus)

        self.delay_spin = QSpinBox()
        self.delay_spin.setObjectName("delaySpin")
        self.delay_spin.setRange(-10000, 10000)
        self.delay_spin.setSuffix("ms")
        self.delay_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delay_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.delay_spin.setFixedWidth(64)  # Adjusted for the 24px buttons
        self.delay_spin.setFixedHeight(24)
        self.delay_spin.valueChanged.connect(self._on_delay_spin_changed)
        delay_row.addWidget(self.delay_spin)

        self.delay_plus = QPushButton("+")
        self.delay_plus.setFixedSize(24, 24)
        self.delay_plus.setObjectName("delaySmallBtn")
        self.delay_plus.setAutoRepeat(True)
        self.delay_plus.setAutoRepeatDelay(300)
        self.delay_plus.setAutoRepeatInterval(50)
        self.delay_plus.clicked.connect(lambda: self.adjust_delay(50))
        delay_row.addWidget(self.delay_plus)

        dsp_main_layout.addLayout(delay_row)

        dsp_main_layout.addStretch()
        content_layout.addLayout(dsp_main_layout)

        # 2. Middle: Audio Tracks List
        list_container = QVBoxLayout()
        list_container.setSpacing(4)

        lbl = QLabel(tr("player.tooltip_audio_track"))
        lbl.setObjectName("popupHeaderLabel")
        self.audio_title_label = lbl
        list_container.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("audioList")
        self.list_widget.setFixedWidth(220)
        self.list_widget.setMinimumHeight(100)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        list_container.addWidget(self.list_widget)

        # Secondary Audio Section
        list_container.addSpacing(8)

        # Separator
        sep_h = QFrame()
        sep_h.setObjectName("aboutSeparator")
        sep_h.setFrameShape(QFrame.Shape.HLine)
        list_container.addWidget(sep_h)

        list_container.addSpacing(4)

        # Enable checkbox
        self.secondary_enabled_cb = QCheckBox(tr("player.enable_secondary_audio"))
        self.secondary_enabled_cb.setObjectName("secondaryAudioCheckbox")
        self.secondary_enabled_cb.toggled.connect(self._on_secondary_enabled_toggled)
        list_container.addWidget(self.secondary_enabled_cb)

        # Container for all secondary audio controls
        self.secondary_container = QWidget()
        container_layout = QVBoxLayout(self.secondary_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        # Secondary volume slider
        sec_vol_layout = QHBoxLayout()
        sec_vol_layout.setSpacing(4)

        self.secondary_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.secondary_volume_slider.setObjectName("secondaryVolumeSlider")
        self.secondary_volume_slider.setRange(0, 100)
        self.secondary_volume_slider.setValue(10)
        self.secondary_volume_slider.valueChanged.connect(
            self._on_secondary_volume_changed
        )
        sec_vol_layout.addWidget(self.secondary_volume_slider, 1)

        self.secondary_volume_label = QLabel("10%")
        self.secondary_volume_label.setObjectName("volumePercentLabel")
        self.secondary_volume_label.setMinimumWidth(35)
        sec_vol_layout.addWidget(self.secondary_volume_label)

        container_layout.addLayout(sec_vol_layout)

        container_layout.addSpacing(4)

        self.secondary_list_widget = QListWidget()
        self.secondary_list_widget.setObjectName("audioList")
        self.secondary_list_widget.setFixedWidth(220)
        self.secondary_list_widget.setFixedHeight(80)
        self.secondary_list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.secondary_list_widget.itemClicked.connect(self._on_secondary_item_clicked)
        container_layout.addWidget(self.secondary_list_widget)

        # Initially hide the container
        self.secondary_container.setVisible(False)

        list_container.addWidget(self.secondary_container)

        content_layout.addLayout(list_container)

        # Separator (Vertical)
        sep = QFrame()
        sep.setObjectName("aboutSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(sep)

        # 3. Right: Volume Slider
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(4)

        self.label = QLabel("100%")
        self.label.setObjectName("volumePercentLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_layout.addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setObjectName("volumeSlider")
        self.slider.setRange(0, 200)
        self.slider.setMinimumHeight(120)
        self.slider.setFixedWidth(50)
        self.slider.valueChanged.connect(self._update_label)
        vol_layout.addWidget(self.slider, 0, Qt.AlignmentFlag.AlignHCenter)

        content_layout.addLayout(vol_layout)

        main_layout.addLayout(content_layout)

        # State
        self.selected_index = -1
        self.items_data = []
        self.secondary_selected_index = -1
        self.secondary_items_data = []
        self.noise_mode = "off"

        # Style
        self._update_label(self.slider.value())
        # Fixed height to prevent resizing when secondary audio is toggled
        self.setFixedHeight(270)

    def cycle_noise_mode(self):
        modes = ["off", "standard", "ai"]
        idx = (modes.index(self.noise_mode) + 1) % len(modes)
        target_mode = modes[idx]
        import logging

        logging.debug(f"DEBUG: popup.cycle_noise_mode() -> {target_mode}")
        self.setNoiseMode(target_mode)

    def setNoiseMode(self, mode):
        import logging

        logging.debug(f"DEBUG: popup.setNoiseMode('{mode}')")
        self.noise_mode = mode
        self.noiseModeChanged.emit(mode)

        # Update button look
        if mode == "off":
            self.noise_btn.setText(tr("player.audio_tools.noise"))
            self.noise_btn.setProperty("active", False)
        else:
            self.noise_btn.setText(f"N:{mode.upper()[:2]}")
            self.noise_btn.setProperty("active", True)

        self.noise_btn.style().unpolish(self.noise_btn)
        self.noise_btn.style().polish(self.noise_btn)

    def _on_mono_toggled(self, checked):
        import logging

        logging.debug(f"DEBUG: popup._on_mono_toggled({checked})")
        self.channelModeChanged.emit("mono" if checked else "normal")

    def adjust_delay(self, delta_ms):
        self.delay_spin.setValue(self.delay_spin.value() + delta_ms)

    def _on_delay_spin_changed(self, val_ms):
        # MPV expects delay in seconds
        self.delayChanged.emit(val_ms / 1000.0)

    def setDelay(self, seconds):
        """External update (e.g. from player load)"""
        self.delay_spin.blockSignals(True)
        self.delay_spin.setValue(int(seconds * 1000))
        self.delay_spin.blockSignals(False)

    # --- Existing List/Slider Logic ---

    # Removing unused delay logic for now or keeping it simple?
    # The user didn't ask for delay in this refined view.

    # --- Existing List/Slider Logic ---

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
        # Standard behavior: close on track selection
        QTimer.singleShot(150, self.hide)

    # --- Secondary Audio Methods ---

    def _on_secondary_enabled_toggled(self, checked):
        self.secondary_container.setVisible(checked)
        self.secondaryAudioToggled.emit(checked)

    def _on_secondary_volume_changed(self, value):
        self.secondary_volume_label.setText(f"{value}%")
        self.secondaryAudioVolumeChanged.emit(value)

    def _on_secondary_item_clicked(self, item):
        index = self.secondary_list_widget.row(item)
        self.secondary_selected_index = index
        self._update_secondary_checkmarks()
        if 0 <= index < len(self.secondary_items_data):
            track_id = self.secondary_items_data[index][0]
            self.secondaryAudioTrackChanged.emit(track_id)

    def clearSecondaryAudio(self):
        self.secondary_list_widget.clear()
        self.secondary_items_data = []
        self.secondary_selected_index = -1

    def addSecondaryAudioItem(self, label, track_id):
        self.secondary_items_data.append((track_id, label))
        self.secondary_list_widget.addItem(label)

    def setSecondaryAudioIndex(self, index):
        self.secondary_selected_index = index
        self._update_secondary_checkmarks()

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

    def setSecondaryVolume(self, volume):
        self.secondary_volume_slider.blockSignals(True)
        self.secondary_volume_slider.setValue(volume)
        self.secondary_volume_slider.blockSignals(False)
        self.secondary_volume_label.setText(f"{volume}%")

    def _update_label(self, value):
        self.label.setText(f"{value}%")
        level = "normal"
        if value > 150:
            level = "danger"
        elif value > 100:
            level = "warning"

        if self.slider.property("level") != level:
            self.slider.setProperty("level", level)
            self.slider.style().unpolish(self.slider)
            self.slider.style().polish(self.slider)

    def update_texts(self):
        self.audio_title_label.setText(tr("player.tooltip_audio_track"))
        self.delay_lbl.setText(tr("player.audio_delay"))

        # Audio tools
        if self.noise_mode == "off":
            self.noise_btn.setText(tr("player.audio_tools.noise"))
        self.noise_btn.setToolTip(tr("player.audio_tools.noise_tooltip"))

        self.comp_btn.setText(tr("player.audio_tools.comp"))
        self.comp_btn.setToolTip(tr("player.audio_tools.comp_tooltip"))

        self.deess_btn.setText(tr("player.audio_tools.deess"))
        self.deess_btn.setToolTip(tr("player.audio_tools.deess_tooltip"))

        self.mono_btn.setText(tr("player.audio_tools.mono"))
        self.mono_btn.setToolTip(tr("player.audio_tools.mono_tooltip"))

        # Secondary audio
        self.secondary_enabled_cb.setText(tr("player.enable_secondary_audio"))

        self._update_checkmarks()
        self._update_secondary_checkmarks()

    def hideEvent(self, event):
        if isinstance(self.parent(), VolumeButton):
            self.parent().on_popup_hidden()
        super().hideEvent(event)


class VolumeButton(QPushButton):
    """Volume button with popup slider and audio selection."""

    volumeChanged = pyqtSignal(int)
    audioChanged = pyqtSignal(int)

    # Forward new signals
    noiseModeChanged = pyqtSignal(str)
    compressorToggled = pyqtSignal(bool)
    deesserToggled = pyqtSignal(bool)
    channelModeChanged = pyqtSignal(str)
    delayChanged = pyqtSignal(float)

    # Secondary Audio Signals
    secondaryAudioToggled = pyqtSignal(bool)
    secondaryAudioTrackChanged = pyqtSignal(int)
    secondaryAudioVolumeChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.icons = load_icons_dict(
            ["volume_mute", "volume_low", "volume_medium", "volume_hight"]
        )
        self.setIcon(self.icons["volume_hight"])
        self.setToolTip(tr("player.tooltip_volume"))

        self.popup = VolumePopup(self)

        # Connect Signals
        self.popup.slider.valueChanged.connect(self._on_slider_changed)
        self.popup.audioChanged.connect(self.audioChanged.emit)

        self.popup.noiseModeChanged.connect(self.noiseModeChanged.emit)
        self.popup.compressorToggled.connect(self.compressorToggled.emit)
        self.popup.deesserToggled.connect(self.deesserToggled.emit)
        self.popup.channelModeChanged.connect(self.channelModeChanged.emit)
        self.popup.delayChanged.connect(self.delayChanged.emit)

        # Connect secondary audio signals
        self.popup.secondaryAudioToggled.connect(self.secondaryAudioToggled.emit)
        self.popup.secondaryAudioTrackChanged.connect(
            self.secondaryAudioTrackChanged.emit
        )
        self.popup.secondaryAudioVolumeChanged.connect(
            self.secondaryAudioVolumeChanged.emit
        )

        self.popup.slider.setValue(100)
        self.last_hide_time = 0
        self.stored_volume = 20

    def on_popup_hidden(self):
        self.last_hide_time = time.time()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_popup()
        elif event.button() == Qt.MouseButton.RightButton:
            # Toggle mute logic
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
        if time.time() - self.last_hide_time < 0.2:
            return
        if self.popup.isVisible():
            self.popup.hide()
            return

        self.popup.ensurePolished()

        # Use fixed height (270px) for consistent positioning
        pw = self.popup.sizeHint().width()
        ph = 270  # Always use fixed height regardless of content
        # Fallback to current width if needed
        pw = max(pw, self.popup.width(), self.popup.minimumWidth())

        button_rect_global = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
        button_center = button_rect_global.center()

        screen = QApplication.screenAt(button_center)
        if not screen:
            screen = (
                self.window().screen()
                if self.window()
                else QApplication.primaryScreen()
            )

        screen_geo = screen.availableGeometry()

        # Center horizontally on the button, but constrain to screen edges
        target_x = button_center.x() - pw // 2
        target_y = button_rect_global.top() - ph - 5

        # Guard against screen edges (increased padding to 30px on right as requested)
        target_x = max(
            screen_geo.left() + 10, min(target_x, screen_geo.right() - pw - 30)
        )
        target_y = max(
            screen_geo.top() + 10, min(target_y, screen_geo.bottom() - ph - 10)
        )

        self.popup.move(target_x, target_y)
        self.popup.show()

    def _on_slider_changed(self, value):
        self._update_icon(value)
        self.volumeChanged.emit(value)

    def _update_icon(self, value):
        if value == 0:
            self.setIcon(self.icons["volume_mute"])
        elif value < 33:
            self.setIcon(self.icons["volume_low"])
        elif value < 66:
            self.setIcon(self.icons["volume_medium"])
        else:
            self.setIcon(self.icons["volume_hight"])

    def update_texts(self):
        self.setToolTip(tr("player.tooltip_volume"))
        self.popup.update_texts()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 5 if delta > 0 else -5
        new_value = max(0, min(200, self.popup.slider.value() + step))
        self.popup.slider.setValue(new_value)
