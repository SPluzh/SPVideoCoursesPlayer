import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenu, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QEvent
from PyQt6.QtGui import QCursor, QAction, QIcon
from translator import tr
from taskbar_progress import TaskbarProgress, TaskbarThumbnailButtons
from constants import RESOURCES_DIR

class FloatingVideoWindow(QWidget):
    """
    Frameless floating window for video playback (Picture-in-Picture).
    """
    closed = pyqtSignal()
    pip_exit_requested = pyqtSignal()

    def __init__(self, video_widget, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        self.video_widget = video_widget
        self.video_widget.setMinimumSize(0, 0) # Remove any min size constraints
        self.resize_margin = 10
        self.min_width = 320
        self.min_height = 180
        self.setMinimumSize(self.min_width, self.min_height)
        
        self.taskbar_progress = TaskbarProgress()
        self.thumbnail_buttons = None
        
        # State for dragging and resizing
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.drag_start_pos = QPoint()
        self.window_start_geo = QRect()
        self.window_start_pos = QPoint()
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.video_widget)
        
        # We need to install event filter on video widget to handle mouse events
        # because it might swallow them, preventing resize/drag if we don't have margins.
        self.video_widget.installEventFilter(self)
        
        # Close button (overlay)
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setObjectName("pipCloseBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self.close_btn.clicked.connect(self.request_close)
        self.close_btn.hide()
        
        # Set initial size
        self.resize(640, 360)
        self.center_on_screen()
        
        self.setMouseTracking(True)
        self.video_widget.setMouseTracking(True)
        
        
        
        # self.set_content_margins() # Removed as requested

    def eventFilter(self, obj, event):
        if obj == self.video_widget:
            # Handle mouse move for resize cursor even over video
            if event.type() == QEvent.Type.MouseMove:
                self.mouseMoveEvent(event)
                # Consume if resizing or dragging or cursor update needed
                if self.resizing or self.dragging or self._get_resize_edge(event.pos()):
                     return True 

            # Ignore double clicks in PiP
            elif event.type() == QEvent.Type.MouseButtonDblClick:
                return True

            # Handle mouse press for resize/drag start
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    edge = self._get_resize_edge(event.pos())
                    if edge:
                        self.resizing = True
                        self.resize_edge = edge
                        self.drag_start_pos = event.globalPosition().toPoint()
                        self.window_start_geo = self.geometry()
                        return True
                
                elif event.button() == Qt.MouseButton.RightButton:
                    # Start dragging on right click
                    self.dragging = True
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.window_start_pos = self.pos()
                    return True
                    
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.RightButton:
                    self.dragging = False
                    return True

        return super().eventFilter(obj, event)


    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.taskbar_progress.set_hwnd(int(self.winId()))
            
            # Initialize thumbnail toolbar buttons for PiP window
            if self.taskbar_progress.taskbar:
                hwnd = int(self.winId())
                self.thumbnail_buttons = TaskbarThumbnailButtons(
                    self.taskbar_progress.taskbar,
                    hwnd,
                    RESOURCES_DIR / 'icons'
                )
                
                def add_and_sync():
                    if self.thumbnail_buttons:
                        self.thumbnail_buttons.add_buttons()
                        # Set initial play state based on video widget
                        if hasattr(self.video_widget, 'is_playing'):
                            self.thumbnail_buttons.update_play_state(self.video_widget.is_playing)

                # Defer to ensure window is fully registered with taskbar
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, add_and_sync)
        except Exception as e:
            logging.error(f"Error setting taskbar HWND or buttons: {e}")

    def center_on_screen(self):
        if self.screen():
            geo = self.frameGeometry()
            center = self.screen().availableGeometry().center()
            geo.moveCenter(center)
            self.move(geo.topLeft())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position close button at top-right
        self.close_btn.move(self.width() - self.close_btn.width(), 0)

    def enterEvent(self, event):
        self.close_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.close_btn.underMouse():
            self.close_btn.hide()
        super().leaveEvent(event)

    def request_close(self):
        """User clicked close button or requested close."""
        self.pip_exit_requested.emit()
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.drag_start_pos = event.globalPosition().toPoint()
                self.window_start_geo = self.geometry()
        
        elif event.button() == Qt.MouseButton.RightButton:
             self.dragging = True
             self.drag_start_pos = event.globalPosition().toPoint()
             self.window_start_pos = self.pos()

    def mouseMoveEvent(self, event):
        # Update cursor shape based on position
        edge = self._get_resize_edge(event.pos())
        if self.resizing:
            self.handle_resize(event.globalPosition().toPoint())
        elif self.dragging:
            diff = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(self.window_start_pos + diff)
        elif edge:
            self.update_cursor(edge)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.resize_edge = None

    def keyPressEvent(self, event):
        vk = event.nativeVirtualKey()
        
        # Physical key P (VK 0x50) toggles PiP regardless of layout
        if vk == 0x50:
            self.pip_exit_requested.emit()
        else:
            super().keyPressEvent(event)

    def _get_resize_edge(self, pos):
        m = self.resize_margin
        w, h = self.width(), self.height()
        
        # Determine vertical part
        v_edge = ""
        if pos.y() < m: v_edge = "top"
        elif pos.y() > h - m: v_edge = "bottom"
        
        # Determine horizontal part
        h_edge = ""
        if pos.x() < m: h_edge = "left"
        elif pos.x() > w - m: h_edge = "right"
        
        # Combine: vertical first (top/bottom) then horizontal (left/right) 
        # to match "topleft", "bottomright" etc.
        edge = v_edge + h_edge
        
        return edge if edge else None

    def update_cursor(self, edge):
        if edge == "left" or edge == "right":
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge == "top" or edge == "bottom":
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ["topleft", "bottomright"]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ["topright", "bottomleft"]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_resize(self, global_pos):
        diff = global_pos - self.drag_start_pos
        geo = self.window_start_geo
        new_geo = QRect(geo)
        ratio = geo.width() / geo.height()
        
        # 1. Apply primary mouse changes to the rectangle
        if "left" in self.resize_edge:
            new_geo.setLeft(geo.left() + diff.x())
        if "right" in self.resize_edge:
            new_geo.setRight(geo.right() + diff.x())
        if "top" in self.resize_edge:
            new_geo.setTop(geo.top() + diff.y())
        if "bottom" in self.resize_edge:
            new_geo.setBottom(geo.bottom() + diff.y())
            
        # 2. Enforce aspect ratio
        # Prioritize Width change if resizing horizontally/corner
        # Prioritize Height change if resizing strictly vertically
        
        is_horizontal = "left" in self.resize_edge or "right" in self.resize_edge
        is_vertical = "top" in self.resize_edge or "bottom" in self.resize_edge
        
        if is_horizontal:
             # Width drives Height
             new_w = new_geo.width()
             new_h = int(new_w / ratio)
             
             if "top" in self.resize_edge:
                 new_geo.setTop(new_geo.bottom() - new_h + 1)
             else:
                 new_geo.setHeight(new_h)
        elif is_vertical:
             # Height drives Width
             new_h = new_geo.height()
             new_w = int(new_h * ratio)
             
             if "left" in self.resize_edge:
                 new_geo.setLeft(new_geo.right() - new_w + 1)
             else: # right or center? mainly only top/bottom edges here
                 # If just top/bottom, we usually expand width to the right or keep center?
                 # Standard behavior: expand right
                 new_geo.setWidth(new_w)

        # 4. Min size check
        if new_geo.width() < self.min_width:
             new_geo.setWidth(self.min_width)
             new_geo.setHeight(int(self.min_width / ratio))
             # Re-adjust position if pulling from left/top
             if "left" in self.resize_edge:
                  new_geo.moveRight(geo.right())
             if "top" in self.resize_edge:
                  new_geo.moveBottom(geo.bottom())

        self.setGeometry(new_geo)


    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        
        # Action to restore to main player
        restore_text = tr("pip.return_to_window")
        if not restore_text or restore_text.startswith("!"):
            restore_text = "Return to Window"
        restore_action = menu.addAction(restore_text)
        restore_action.triggered.connect(self.request_close)
        
        # Action to exit application (or just close pip?)
        # "Exit" usually means exit app. "Close" means close window.
        # But this window is part of the app.
        pass

    def play_pause(self):
        # Delegate to video widget if possible, or just ignore since widget handles it
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            pass # Escape is disabled as per request
        elif event.key() == Qt.Key.Key_P:
            self.request_close()
        else:
            super().keyPressEvent(event)


class PiPManager:
    """
    Manages Picture-in-Picture mode lifecycle.

    Coordinates the FloatingVideoWindow, main window visibility,
    video widget detachment/reattachment, and taskbar progress swapping.
    """

    def __init__(self, main_window, video_player, taskbar_progress):
        self.main_window = main_window
        self.video_player = video_player
        self.taskbar_progress = taskbar_progress
        self.floating_window = None
        self.floating_window_active = False
        self.pip_geometry = None

    @property
    def is_active(self):
        return self.floating_window and self.floating_window.isVisible()

    def toggle(self):
        """Toggle Picture-in-Picture mode."""
        logging.debug("toggle_pip_mode called")
        if self.is_active:
            logging.debug("Floating window visible, exiting PiP")
            self.exit_pip()
        else:
            logging.debug("Floating window not visible/exists, entering PiP")
            self.enter_pip()

    def enter_pip(self):
        """Enter Picture-in-Picture mode."""
        logging.debug("enter_pip_mode start")
        if self.is_active:
            logging.debug("Already in PiP mode, ignoring")
            return

        if not self.video_player.current_file:
            logging.debug("No current file, cannot enter PiP")
            return

        try:
            # Detach video widget
            logging.debug("Detaching video widget...")
            video_widget = self.video_player.detach_video_widget()
            logging.debug(f"Detached widget: {video_widget}")

            # Create floating window
            logging.debug("Creating FloatingVideoWindow...")
            self.floating_window = FloatingVideoWindow(video_widget)
            logging.debug("Connecting pip_exit_requested...")
            self.floating_window.pip_exit_requested.connect(self.exit_pip)
            logging.debug("Showing floating window...")
            if self.pip_geometry:
                self.floating_window.restoreGeometry(self.pip_geometry)
            self.floating_window.show()

            self.floating_window_active = True

            # Hide main window
            logging.debug("Hiding main window...")
            self.main_window.hide()

            # Swap taskbar progress to PiP window (after show, so HWND is set)
            if self.floating_window.taskbar_progress._initialized:
                self.video_player.taskbar_progress = self.floating_window.taskbar_progress
            logging.debug("enter_pip_mode finished")

        except Exception as e:
            logging.error(f"ERROR in enter_pip_mode: {e}")
            import traceback
            traceback.print_exc()

    def exit_pip(self):
        """Exit Picture-in-Picture mode."""
        logging.debug("exit_pip_mode start")
        if not self.floating_window:
            logging.debug("No floating window to exit")
            return

        try:
            # Get widget back
            logging.debug("Getting video widget back...")
            video_widget = self.floating_window.video_widget
            if not video_widget:
                 logging.error("Floating window has no video widget!")

            logging.debug("Reattaching video widget...")
            self.video_player.reattach_video_widget(video_widget)

            # Destroy floating window
            if self.floating_window:
                self.pip_geometry = self.floating_window.saveGeometry()
                logging.debug("Closing floating window...")
                self.floating_window.close()
                self.floating_window = None
            self.floating_window_active = False

            # Show main window
            logging.debug("Showing main window...")

            # Restore taskbar progress to main window
            self.video_player.taskbar_progress = self.taskbar_progress

            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            logging.debug("exit_pip_mode finished")

        except Exception as e:
            logging.error(f"ERROR in exit_pip_mode: {e}")
            import traceback
            traceback.print_exc()

