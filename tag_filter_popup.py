from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor

from translator import tr


class TagFilterPopup(QWidget):
    """A popup widget containing a checkable list of tags for filtering"""
    filter_changed = pyqtSignal(set) # Emits set of checked tag IDs

    def __init__(self, all_tags, selected_ids, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setObjectName("tagFilterPopup")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel(tr("player.filter_tags") if tr("player.filter_tags") != "player.filter_tags" else "Tags")
        header_label.setObjectName("popupHeaderLabel")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)

        # Helper layout for buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.btn_select_all = QPushButton(tr("library.select_all"))
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setObjectName("audioFilterBtn") # Re-use audio filter btn style for compact look
        self.btn_select_all.clicked.connect(self.select_all)
        
        self.btn_deselect_all = QPushButton(tr("library.deselect_all"))
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.setObjectName("audioFilterBtn")
        self.btn_deselect_all.clicked.connect(self.deselect_all)

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_deselect_all)
        
        main_layout.addLayout(btn_layout)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("tagFilterList")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        
        # Populate list
        if not all_tags:
             item = QListWidgetItem(tr("library.no_tags_available"))
             item.setFlags(Qt.ItemFlag.NoItemFlags)
             self.list_widget.addItem(item)
             self.btn_select_all.setEnabled(False)
             self.btn_deselect_all.setEnabled(False)
        else:
            for tag in all_tags:
                item = QListWidgetItem(tag['name'])
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(Qt.CheckState.Checked if tag['id'] in selected_ids else Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, tag['id'])
                
                if tag.get('color'):
                    # Use slightly larger icon to match new context menu style? Or keep standard?
                    # Let's keep specific 14x14 for now, or match context menu 16x16
                    pixmap = QPixmap(14, 14)
                    pixmap.fill(QColor(tag['color']))
                    item.setIcon(QIcon(pixmap))
                
                self.list_widget.addItem(item)
                
        main_layout.addWidget(self.list_widget)

        # Calculate size behavior similar to VolumePopup (adjustSize or fixed width)
        # VolumePopup uses setMinimumWidth(380) but that's because of horizontal layout
        # Tags are vertical list.
        self.setMinimumWidth(250)
        
        rows = self.list_widget.count()
        # Cap height reasonable for a popup
        row_height = self.list_widget.sizeHintForRow(0) if rows > 0 else 24
        list_height = rows * row_height + 5 
        list_height = min(400, max(100, list_height))
        
        # Total height approximation
        self.list_widget.setFixedHeight(list_height)
        self.adjustSize()

    def select_all(self):
        self._set_all_checked(Qt.CheckState.Checked)

    def deselect_all(self):
        self._set_all_checked(Qt.CheckState.Unchecked)

    def _set_all_checked(self, state):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(state)
        self.list_widget.blockSignals(False)
        self._on_item_changed(None)

    def _on_item_changed(self, item):
        checked_ids = set()
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                tid = it.data(Qt.ItemDataRole.UserRole)
                if tid is not None:
                    checked_ids.add(tid)
        self.filter_changed.emit(checked_ids)
