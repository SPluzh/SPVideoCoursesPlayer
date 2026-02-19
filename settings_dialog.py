import sys
import os
import configparser
import time
import io
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem, QPushButton,
    QHBoxLayout, QFileDialog, QStyle, QMessageBox, QLabel, QProgressBar, QTextEdit,
    QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QTextCursor, QIcon

from translator import tr
from styles import DARK_STYLE

from constants import RESOURCES_DIR
from progress_dialog import ScanProgressDialog, UpdateProgressDialog
from icon_manager import load_icons_dict
from config_manager import ConfigManager
from constants import ROOT_DIR, DATA_DIR

from utils import resolve_binary_path



class SettingsDialog(QDialog):
    def __init__(self, parent=None, config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.config = ConfigManager(self.config_file, ROOT_DIR, DATA_DIR)
        self.setWindowTitle(tr('settings.title'))
        self.setMinimumWidth(650)
        self.load_icons()
        self.setup_ui()
        self.load_current_settings()

    def load_icons(self):
        icon_names = ["menu_scan", "add", "edit", "delete", "save", "upload", "download", "check", "fail"]
        self.icons = load_icons_dict(icon_names)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        content_layout = QHBoxLayout()
        
        library_group = QGroupBox(tr('settings.library_group'))
        library_layout = QVBoxLayout()

        self.pathslist = QTreeWidget()
        self.pathslist.setHeaderHidden(True)
        # Styles moved to resources/styles/dark.qss
        self.pathslist.itemChanged.connect(self.on_path_checked)
        library_layout.addWidget(self.pathslist)

        buttons = QHBoxLayout()
        add_btn = QPushButton(tr('settings.add'))
        add_btn.setIcon(self.icons.get('add', QIcon()))
        add_btn.clicked.connect(self.add_path)
        buttons.addWidget(add_btn)

        edit_btn = QPushButton(tr('settings.edit'))
        edit_btn.setIcon(self.icons.get('edit', QIcon()))
        edit_btn.clicked.connect(self.edit_path)
        buttons.addWidget(edit_btn)

        remove_btn = QPushButton(tr('settings.remove'))
        remove_btn.setIcon(self.icons.get('delete', QIcon()))
        remove_btn.clicked.connect(self.remove_path)
        buttons.addWidget(remove_btn)

        library_layout.addLayout(buttons)

        self.scan_btn = QPushButton(tr('settings.scan'))
        self.scan_btn.setIcon(self.icons.get('menu_scan', QIcon()))
        self.scan_btn.clicked.connect(self.start_scan)
        library_layout.addWidget(self.scan_btn)

        library_group.setLayout(library_layout)
        content_layout.addWidget(library_group, 2)

        deps_group = QGroupBox(tr('settings.dependencies_group'))
        deps_layout = QVBoxLayout()
        
        self.libmpv_btn = QPushButton(tr('settings.libmpv_checking'))
        self.libmpv_btn.clicked.connect(self.update_libmpv)
        deps_layout.addWidget(self.libmpv_btn)

        self.ffmpeg_btn = QPushButton(tr('settings.ffmpeg_checking'))
        self.ffmpeg_btn.clicked.connect(self.update_ffmpeg)
        deps_layout.addWidget(self.ffmpeg_btn)
        
        deps_layout.addStretch()

        self.auto_update_chk = QCheckBox(tr('updater.check_updates_auto'))
        self.auto_update_chk.setChecked(True)
        deps_layout.addWidget(self.auto_update_chk)

        deps_group.setLayout(deps_layout)

        storage_group = QGroupBox(tr('settings.storage_group'))
        storage_layout = QVBoxLayout()
        
        self.clear_data_btn = QPushButton(tr('settings.clear_data'))
        self.clear_data_btn.setObjectName("clearDataBtn")
        self.clear_data_btn.setIcon(self.icons.get('delete', QIcon()))
        self.clear_data_btn.clicked.connect(self.clear_metadata)
        storage_layout.addWidget(self.clear_data_btn)
        
        storage_layout.addStretch()
        storage_group.setLayout(storage_layout)
        
        right_column = QVBoxLayout()
        right_column.addWidget(deps_group)
        right_column.addWidget(storage_group)
        content_layout.addLayout(right_column, 1)

        
        main_layout.addLayout(content_layout)
        
        QTimer.singleShot(100, self.check_libmpv_version)
        QTimer.singleShot(200, self.check_ffmpeg_version)

        save_btn = QPushButton(tr('settings.save'))
        save_btn.setIcon(self.icons.get('save', QIcon()))
        save_btn.clicked.connect(self.save_settings)
        main_layout.addWidget(save_btn)

    def add_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, tr('dialog.select_directory')
        )
        if directory:
            # Check if path already exists
            for i in range(self.pathslist.topLevelItemCount()):
                if self.pathslist.topLevelItem(i).text(0) == directory:
                    return

            item = QTreeWidgetItem([directory])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)
            self.pathslist.addTopLevelItem(item)
            self._validate_path(item)

    def edit_path(self):
        current = self.pathslist.currentItem()
        if not current:
            return
        directory = QFileDialog.getExistingDirectory(
            self,
            tr('dialog.select_directory'),
            current.text(0)
        )
        if directory:
            current.setText(0, directory)
            self._validate_path(current)

    def clear_metadata(self):
        """Clear all metadata from DB via parent window."""
        reply = QMessageBox.question(
            self, tr('settings.clear_title'),
            tr('settings.clear_confirm_text'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Use parent method to clear data
            if self.parent() and hasattr(self.parent(), 'clear_metadata_force'):
                if self.parent().clear_metadata_force():
                    # Show status on parent
                    if hasattr(self.parent(), 'info_label'):
                        self.parent().info_label.setText(tr('settings.data_cleared'))
                    QMessageBox.information(self, tr('settings.clear_title'), tr('settings.clear_success'))
                else:
                    QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.clear_error'))
            else:
                # If parent cannot, try directly (logic duplication)
                if self.parent() and hasattr(self.parent(), 'db'):
                    if self.parent().db.clear_all_metadata():
                        self.parent().db.vacuum()
                        if hasattr(self.parent(), 'load_courses'):
                            self.parent().load_courses()
                        QMessageBox.information(self, tr('settings.clear_title'), tr('settings.clear_success'))
                    else:
                        QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.clear_error'))
                else:
                    QMessageBox.critical(self, tr('settings.clear_title'), tr('settings.db_not_available'))

    def remove_path(self):
        current = self.pathslist.currentItem()
        if not current:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(tr('settings.confirm'))
        msg.setText(tr('settings.removeconfirm'))
        msg.setIcon(QMessageBox.Icon.Question)
        yes_button = msg.addButton(tr('settings.yes'), QMessageBox.ButtonRole.YesRole)
        no_button = msg.addButton(tr('settings.no'), QMessageBox.ButtonRole.NoRole)
        msg.exec()

        if msg.clickedButton() == yes_button:
            path_to_remove = current.text(0)
            norm = os.path.normpath(path_to_remove)
            if not hasattr(self, '_deleted_paths'):
                self._deleted_paths = []
            if norm not in self._deleted_paths:
                self._deleted_paths.append(norm)

            index = self.pathslist.indexOfTopLevelItem(current)
            self.pathslist.takeTopLevelItem(index)

    def on_path_checked(self, item, column):
        """Update visual style when path active state changes."""
        font = item.font(0)
        if item.checkState(0) == Qt.CheckState.Unchecked:
            font.setStrikeOut(True)
            # Optional: set color to gray to indicate disabled state further
            # item.setForeground(0, Qt.GlobalColor.gray)
        else:
            font.setStrikeOut(False)
            # item.setForeground(0, Qt.GlobalColor.black) # Restore color if needed
            
        item.setFont(0, font)

    def get_paths_list(self):
        paths = []
        for i in range(self.pathslist.topLevelItemCount()):
            paths.append(self.pathslist.topLevelItem(i).text(0))
        return paths

    def load_current_settings(self):
        self._deleted_paths = []  # сброс при каждой загрузке
        self.pathslist.clear()
        
        paths_str = self.config.get_library_paths()
        excluded_paths = self.config.get_excluded_library_paths()

        if paths_str:
            for path in paths_str.split(';'):
                path = path.strip()
                if path:
                    item = QTreeWidgetItem([path])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    
                    if os.path.normpath(path) in excluded_paths:
                        item.setCheckState(0, Qt.CheckState.Unchecked)
                        font = item.font(0)
                        font.setStrikeOut(True)
                        item.setFont(0, font)
                    else:
                        item.setCheckState(0, Qt.CheckState.Checked)
                        
                    self.pathslist.addTopLevelItem(item)
                    self._validate_path(item)

        self.auto_update_chk.setChecked(self.config.get_check_updates_on_start())

    def _validate_path(self, item):
        path = item.text(0)
        if os.path.exists(path):
            icon = self.icons.get('check', self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            item.setIcon(0, icon)
            item.setToolTip(0, tr('settings.path_valid', path=path))
        else:
            icon = self.icons.get('fail', self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
            item.setIcon(0, icon)
            item.setToolTip(0, tr('settings.path_invalid', path=path))

    def save_settings(self):
        paths = []
        excluded_paths = []
        for i in range(self.pathslist.topLevelItemCount()):
            item = self.pathslist.topLevelItem(i)
            path = item.text(0)
            paths.append(path)
            if item.checkState(0) == Qt.CheckState.Unchecked:
                excluded_paths.append(path)

        # также включаем пути, которые были удалены в этой сессии настроек
        deleted = getattr(self, '_deleted_paths', [])
        for p in deleted:
            if p not in excluded_paths:
                excluded_paths.append(p)

        self.config.set_library_paths(paths)
        self.config.set_excluded_library_paths(excluded_paths)
        self.config.set_check_updates_on_start(self.auto_update_chk.isChecked())

        self.accept()

    def start_scan(self):
        # Only scan checked (active) paths
        paths = []
        for i in range(self.pathslist.topLevelItemCount()):
            item = self.pathslist.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                paths.append(item.text(0))
                
        if not paths:
            QMessageBox.warning(
                self,
                tr('settings.warning'),
                tr('settings.specify_path')
            )
            return

        # Save settings without closing
        self._save_settings_only()

        # Show scan dialog directly
        dialog = ScanProgressDialog(self)
        ffmpeg_path = None
        ffprobe_path = None
        if self.parent() and hasattr(self.parent(), 'ffmpeg_path'):
            ffmpeg_path = self.parent().ffmpeg_path
            ffprobe_path = self.parent().ffprobe_path
            
        dialog.start_scan(self.config_file, paths, ffmpeg_path, ffprobe_path)
        
        if self.parent() and hasattr(self.parent(), 'load_courses'):
            dialog.scanner_thread.finished_scan.connect(
                lambda v, f: self.parent().load_courses()
            )
        dialog.exec()

    def _save_settings_only(self):
        """Save settings without closing the dialog"""
        paths = self.get_paths_list()
        # Find excluded based on check state matching save_settings logic
        # But get_paths_list only returns text.
        # Let's logic it out properly or reuse logic.
        # Simpler: call set_library_paths with whatever we have?
        # But wait, logic in save_settings calculates excluded_paths too.
        # This _save_settings_only implementation in current file ONLY saves 'paths', not 'excluded_paths'!
        # That seems like a bug or simplification in original code.
        # We should probably fix it to be consistent.
        
        paths = []
        excluded_paths = []
        for i in range(self.pathslist.topLevelItemCount()):
            item = self.pathslist.topLevelItem(i)
            path = item.text(0)
            paths.append(path)
            if item.checkState(0) == Qt.CheckState.Unchecked:
                excluded_paths.append(path)

        deleted = getattr(self, '_deleted_paths', [])
        for p in deleted:
            if p not in excluded_paths:
                excluded_paths.append(p)

        self.config.set_library_paths(paths)
        self.config.set_excluded_library_paths(excluded_paths)

    def check_libmpv_version(self):
        """Check if libmpv-2.dll is present in bin folder"""
        try:
            dll_path = self.config.get_libmpv_path()
            
            if dll_path.exists():
                self.libmpv_btn.setText(f" libmpv-2.dll")
                self.libmpv_btn.setIcon(self.icons.get('check', QIcon()))
                self.libmpv_btn.setToolTip(tr('settings.libmpv_up_to_date'))
            else:
                self.libmpv_btn.setText(f" libmpv-2.dll")
                self.libmpv_btn.setIcon(self.icons.get('download', QIcon()))
                self.libmpv_btn.setToolTip(tr('settings.libmpv_not_installed'))
        except Exception as e:
            self.libmpv_btn.setText(f" libmpv-2.dll")
            self.libmpv_btn.setIcon(self.icons.get('fail', QIcon()))
            self.libmpv_btn.setToolTip(str(e))

    def update_libmpv(self):
        """Update libmpv-2.dll with progress dialog"""
        from update_libmpv import update_libmpv as do_update
        
        dialog = UpdateProgressDialog(self, tr('libmpv_updater.title'))
        dialog.start_update(do_update)
        dialog.exec()
        
        self.check_libmpv_version()

    def check_ffmpeg_version(self):
        """Check if FFmpeg/ffprobe are present in bin folder"""
        try:
            ffmpeg_path = self.config.get_ffmpeg_path()
            ffprobe_path = self.config.get_ffprobe_path()
            
            if ffmpeg_path.exists() and ffprobe_path.exists():
                self.ffmpeg_btn.setText(f" FFmpeg & ffprobe")
                self.ffmpeg_btn.setIcon(self.icons.get('check', QIcon()))
                self.ffmpeg_btn.setToolTip(tr('settings.ffmpeg_found'))
            else:
                self.ffmpeg_btn.setText(f" {tr('settings.ffmpeg_update')}")
                self.ffmpeg_btn.setIcon(self.icons.get('download', QIcon()))
                self.ffmpeg_btn.setToolTip(tr('settings.ffmpeg_not_found'))
        except Exception as e:
            self.ffmpeg_btn.setText(f" FFmpeg")
            self.ffmpeg_btn.setIcon(self.icons.get('fail', QIcon()))
            self.ffmpeg_btn.setToolTip(str(e))

    def update_ffmpeg(self):
        """Download FFmpeg with progress dialog"""
        from update_ffmpeg import download_ffmpeg
        
        # Wrap download_ffmpeg to match the expected signature (no args or default force=True)
        def do_update():
            return download_ffmpeg(force=True)
            
        dialog = UpdateProgressDialog(self, tr('ffmpeg_updater.title'))
        dialog.start_update(do_update)
        dialog.exec()
        
        self.check_ffmpeg_version()

