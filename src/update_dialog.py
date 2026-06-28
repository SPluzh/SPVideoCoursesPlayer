"""
Update confirmation dialog for SPVideoCoursesPlayer.

Shows available update info, changelog, and action buttons.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt

from translator import tr


class UpdateDialog(QDialog):
    """Dialog shown when a new app version is available."""

    # Result codes
    UPDATE_NOW = 1
    SKIP_VERSION = 2
    LATER = 0

    def __init__(self, parent=None, update_info: dict = None):
        super().__init__(parent)
        self.update_info = update_info or {}
        self.result_action = self.LATER
        self.setWindowTitle(tr('updater.title'))
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel(tr('updater.available', version=self.update_info.get('latest', '?')))
        title.setObjectName("updateDialogTitle")
        layout.addWidget(title)

        # Version info
        current_label = QLabel(tr('updater.current_version', version=self.update_info.get('current', '?')))
        layout.addWidget(current_label)

        new_label = QLabel(tr('updater.new_version', version=self.update_info.get('latest', '?')))
        new_label.setObjectName("updateDialogNewVersion")
        layout.addWidget(new_label)

        # Changelog
        changelog_title = QLabel(tr('updater.changelog'))
        layout.addWidget(changelog_title)

        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        changelog_content = self.update_info.get('changelog', '')
        if changelog_content:
            self.changelog_text.setMarkdown(changelog_content)
        else:
            self.changelog_text.setPlainText("—")
        layout.addWidget(self.changelog_text, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        skip_btn = QPushButton(tr('updater.skip_version'))
        skip_btn.clicked.connect(self._on_skip)
        btn_layout.addWidget(skip_btn)

        btn_layout.addStretch()

        later_btn = QPushButton(tr('updater.later'))
        later_btn.clicked.connect(self._on_later)
        btn_layout.addWidget(later_btn)

        update_btn = QPushButton(tr('updater.update_now'))
        update_btn.setDefault(True)
        update_btn.setObjectName("updateNowBtn")
        update_btn.clicked.connect(self._on_update)
        btn_layout.addWidget(update_btn)

        layout.addLayout(btn_layout)

    def _on_update(self):
        self.result_action = self.UPDATE_NOW
        self.accept()

    def _on_skip(self):
        self.result_action = self.SKIP_VERSION
        self.reject()

    def _on_later(self):
        self.result_action = self.LATER
        self.reject()
