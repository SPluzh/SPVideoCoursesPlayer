from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QColorDialog, QMenu, QMessageBox,
    QWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QBrush, QPen

from translator import tr

class TagsDialog(QDialog):
    def __init__(self, parent, db, file_path):
        super().__init__(parent)
        self.setWindowTitle(tr('tags.title') or "Manage Tags")
        self.setMinimumSize(400, 500)
        self.db = db
        self.file_path = file_path
        
        self.selected_color = "#3498db" # Default blue
        
        self.layout = QVBoxLayout(self)
        
        # Tag List
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.list_widget)
        
        # New Tag Creation
        create_group = QWidget()
        create_layout = QHBoxLayout(create_group)
        create_layout.setContentsMargins(0, 0, 0, 0)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr('tags.new_tag_name') or "New Tag Name")
        create_layout.addWidget(self.name_input)
        
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(24, 24)
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #555; border-radius: 4px;")
        self.color_btn.clicked.connect(self.pick_color)
        create_layout.addWidget(self.color_btn)
        
        self.add_btn = QPushButton("Str(Add)")
        self.add_btn.setText(tr('tags.add_btn') or "Add")
        self.add_btn.clicked.connect(self.create_tag)
        create_layout.addWidget(self.add_btn)
        
        self.layout.addWidget(create_group)
        
        # Dialog Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(tr('dialog.save') or "Save")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton(tr('dialog.cancel') or "Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.layout.addLayout(btn_layout)
        
        self.load_tags()

    def load_tags(self):
        self.list_widget.clear()
        
        # Get all tags
        all_tags = self.db.get_tags()
        # Get tags for this video
        current_tags = self.db.get_video_tags(self.file_path)
        current_tag_ids = {t['id'] for t in current_tags}
        
        for tag in all_tags:
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, tag['id'])
            
            # Custom widget for checkbox + colored label
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 2, 5, 2)
            
            chk = QCheckBox()
            chk.setChecked(tag['id'] in current_tag_ids)
            chk.stateChanged.connect(lambda state, tid=tag['id']: self.on_tag_toggled(tid, state))
            layout.addWidget(chk)
            
            # Color Badge
            lbl = QLabel(tag['name'])
            lbl.setStyleSheet(f"background-color: {tag['color']}; padding: 3px 8px; border-radius: 10px; color: #fff; font-weight: bold;")
            layout.addWidget(lbl)
            
            layout.addStretch()
            
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

    def on_tag_toggled(self, tag_id, state):
        # We can either save immediately or wait for "Save"
        # Since I'm using `accept`/`reject`, I should probably store changes and apply on accept.
        # But for simplicity in this iteration, I'll apply immediately, 
        # OR I can just read the checkboxes on accept. 
        # The QCheckBox is inside a widget item, accessing it later is slightly annoying but doable.
        # Actually, let's keep track of selected IDs in a set.
        pass

    def get_selected_tag_ids(self):
        selected_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            tag_id = item.data(Qt.ItemDataRole.UserRole)
            widget = self.list_widget.itemWidget(item)
            chk = widget.findChild(QCheckBox)
            if chk and chk.isChecked():
                selected_ids.append(tag_id)
        return selected_ids

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self, tr('tags.select_color') or "Select Color")
        if color.isValid():
            self.selected_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #555; border-radius: 4px;")

    def create_tag(self):
        name = self.name_input.text().strip()
        if not name:
            return
            
        self.db.create_tag(name, self.selected_color)
        self.name_input.clear()
        self.load_tags()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
            
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu()
        delete_action = menu.addAction(tr('tags.delete') or "Delete Tag")
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        
        if action == delete_action:
            confirm = QMessageBox.question(
                self, 
                tr('dialog.confirm') or "Confirm",
                tr('tags.confirm_delete') or "Are you sure you want to delete this tag?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.db.delete_tag(tag_id)
                self.load_tags()

    def accept(self):
        # Apply changes
        new_tag_ids = set(self.get_selected_tag_ids())
        
        # Get old tags to minimize DB writes
        current_tags = self.db.get_video_tags(self.file_path)
        old_tag_ids = {t['id'] for t in current_tags}
        
        to_add = new_tag_ids - old_tag_ids
        to_remove = old_tag_ids - new_tag_ids
        
        for tid in to_add:
            self.db.add_tag_to_video(self.file_path, tid)
            
        for tid in to_remove:
            self.db.remove_tag_from_video(self.file_path, tid)
            
        super().accept()
