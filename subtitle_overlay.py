import string
import logging
from PyQt6.QtWidgets import QFrame, QTextEdit, QVBoxLayout, QApplication, QWidget, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect, QEvent
from PyQt6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat

class SubtitleTextEdit(QTextEdit):
    wordHovered = pyqtSignal(str, QPoint)      # (word, global_pos)
    selectionSelected = pyqtSignal(str, QPoint) # (text, global_pos)
    hoverCleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setAcceptRichText(True)
        self.setMouseTracking(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Transparent background for the text edit area
        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, Qt.GlobalColor.transparent)
        self.setPalette(palette)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._on_hover_timeout)

        self.current_hovered_word = ""
        self.current_hovered_cursor = None
        self.hover_pos = QPoint()

    def _on_hover_timeout(self):
        try:
            if self.current_hovered_word and self.current_hovered_cursor:
                # Highlight the word
                self.highlight_word(self.current_hovered_cursor)
                self.wordHovered.emit(self.current_hovered_word, self.hover_pos)
        except Exception as e:
            logging.error(f"Error in _on_hover_timeout: {e}", exc_info=True)

    def highlight_word(self, cursor):
        try:
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            
            format = QTextCharFormat()
            # Premium highlight: gold semi-transparent background
            format.setBackground(QColor(255, 215, 0, 80)) 
            selection.format = format
            self.setExtraSelections([selection])
        except Exception as e:
            logging.error(f"Error in highlight_word: {e}", exc_info=True)

    def clear_highlight(self):
        try:
            self.setExtraSelections([])
            self.current_hovered_word = ""
            self.current_hovered_cursor = None
            self.hoverCleared.emit()
        except Exception as e:
            logging.error(f"Error in clear_highlight: {e}", exc_info=True)

    def mouseMoveEvent(self, event):
        try:
            # Let default QTextEdit process selection / drag
            super().mouseMoveEvent(event)

            # If user is selecting text (left button is down), do not trigger hover translation
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.hover_timer.stop()
                return

            # If there is already an active selection, do not trigger hover translation
            if self.textCursor().hasSelection():
                self.hover_timer.stop()
                return

            pos = event.position().toPoint()
            cursor = self.cursorForPosition(pos)

            if not cursor.isNull():
                # Check if mouse is actually over a character
                rect = self.cursorRect(cursor)
                char_width = 12
                char_height = rect.height()
                # Expand caret line to character size for hit-testing
                expanded_rect = QRect(rect.x() - char_width, rect.y(), char_width * 2, char_height)
                
                if expanded_rect.contains(pos):
                    cursor.select(QTextCursor.SelectionType.WordUnderCursor)
                    word = cursor.selectedText()
                    cleaned_word = word.strip(string.punctuation + " \n\r\t»«“”‘’")
                    
                    if cleaned_word and cleaned_word.isalpha():
                        if cleaned_word != self.current_hovered_word:
                            self.current_hovered_word = cleaned_word
                            self.current_hovered_cursor = cursor
                            self.hover_pos = self.mapToGlobal(pos)
                            logging.debug(f"Subtitle word hovered: '{cleaned_word}', position: {self.hover_pos}")
                            # Reset timer
                            self.hover_timer.start(300) # 300ms debounce
                        return

            # If not over a word, clear
            self.hover_timer.stop()
            if self.current_hovered_word:
                self.clear_highlight()
        except Exception as e:
            logging.error(f"Error in mouseMoveEvent: {e}", exc_info=True)

    def mouseReleaseEvent(self, event):
        try:
            super().mouseReleaseEvent(event)
            cursor = self.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                # Clean punctuation and numbers if appropriate, or just strip
                if selected_text:
                    global_pos = self.mapToGlobal(event.position().toPoint())
                    logging.debug(f"Subtitle text selected: '{selected_text}', position: {global_pos}")
                    self.selectionSelected.emit(selected_text, global_pos)
        except Exception as e:
            logging.error(f"Error in mouseReleaseEvent: {e}", exc_info=True)

    def leaveEvent(self, event):
        try:
            self.hover_timer.stop()
            cursor = self.textCursor()
            if cursor.hasSelection():
                cursor.clearSelection()
                self.setTextCursor(cursor)
            self.clear_highlight()
            super().leaveEvent(event)
        except Exception as e:
            logging.error(f"Error in leaveEvent: {e}", exc_info=True)

    def enterEvent(self, event):
        try:
            parent = self.parent()
            if parent and hasattr(parent, "mouseEntered"):
                parent.mouseEntered.emit()
            super().enterEvent(event)
        except Exception as e:
            logging.error(f"Error in enterEvent: {e}", exc_info=True)


class SubtitleOverlayWidget(QFrame):
    mouseEntered = pyqtSignal()
    mouseLeft = pyqtSignal()

    def __init__(self, video_widget, player_window):
        super().__init__(video_widget, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.video_widget = video_widget
        self.player_window = player_window
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setObjectName("SubtitleOverlayWidget")
        
        # Overlay Style: transparent background for QFrame to avoid double-painting,
        # but let paintEvent handle the actual rounded translucent drawing.
        self.setStyleSheet("""
            #SubtitleOverlayWidget {
                background: transparent;
                border: none;
            }
        """)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 8, 50, 8)
        layout.setSpacing(0)

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        # Text Edit
        self.text_edit = SubtitleTextEdit(self)
        self.text_edit.document().setDocumentMargin(0)
        self.text_edit.setMinimumHeight(0)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.text_edit)

        # Connect event filters to dynamically update geometry
        if self.video_widget:
            self.video_widget.installEventFilter(self)
        if self.player_window:
            self.player_window.installEventFilter(self)

        self.text_color = "#FFFFFF"
        self.outline_color = "#000000"
        self.font_scale = 1.0
        self.current_text = ""
        self.current_font_size = 0

        self.update_geometry()

    def enterEvent(self, event):
        try:
            self.mouseEntered.emit()
            super().enterEvent(event)
        except Exception as e:
            logging.error(f"Error in enterEvent: {e}", exc_info=True)

    def leaveEvent(self, event):
        try:
            from PyQt6.QtGui import QCursor
            if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                self.mouseLeft.emit()
            super().leaveEvent(event)
        except Exception as e:
            logging.error(f"Error in leaveEvent: {e}", exc_info=True)

    def get_calculated_font_size(self):
        if self.video_widget:
            vh = self.video_widget.height()
        else:
            vh = 720
        # MPV reference height is 720, adjusted base font size to 27 (half of MPV's 55)
        # to match native rendering size in this overlay context.
        base_font_size = 35
        calculated = int(base_font_size * (vh / 720.0) * self.font_scale)
        return max(16, calculated)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        
        # Premium dark translucent background (alpha = 170)
        bg_color = QColor(0, 0, 0, 170)
        painter.fillRect(self.rect(), bg_color)

    def _should_be_visible(self) -> bool:
        if not self.video_widget or not self.video_widget.isVisible():
            return False
        if not self.text_edit.toPlainText().strip():
            return False

        win = getattr(self, '_installed_window', None)
        if not win and self.player_window:
            win = self.player_window.window()

        if win and win.isMinimized():
            return False

        return True

    def update_visibility(self):
        try:
            if self._should_be_visible():
                self.show()
                self.raise_()
            else:
                self.hide()
        except Exception as e:
            logging.error(f"Error updating visibility: {e}", exc_info=True)

    def set_text(self, text):
        self.current_text = text
        if not text:
            self.text_edit.clear()
            self.hide()
            return

        # Render centered text
        font_size = self.get_calculated_font_size()
        self.current_font_size = font_size
        html = f"""
        <div style="text-align: center; color: {self.text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {font_size}px; font-weight: normal; line-height: 1.2;">
            {text}
        </div>
        """
        self.text_edit.setHtml(html)
        
        # Ensure geometry is updated for the new text
        self.update_geometry()
        
        # Check visibility conditions
        if self._should_be_visible():
            self.show()
            # Raise overlay to ensure it's on top of any video surface
            self.raise_()
        else:
            self.hide()

    def set_subtitle_style(self, text_color, outline_color, font_scale):
        self.text_color = text_color
        self.outline_color = outline_color
        self.font_scale = font_scale
        # Refresh current text if any
        self.set_text(self.current_text)

    def _check_install_window_filter(self):
        if self.video_widget:
            win = self.video_widget.window()
            if win and win != self.video_widget:
                if not hasattr(self, '_installed_window') or self._installed_window != win:
                    # Remove from old if any
                    if hasattr(self, '_installed_window') and self._installed_window:
                        try:
                            self._installed_window.removeEventFilter(self)
                        except Exception:
                            pass
                    win.installEventFilter(self)
                    self._installed_window = win

    def showEvent(self, event):
        self._check_install_window_filter()
        super().showEvent(event)

    def hideEvent(self, event):
        try:
            for child in self.findChildren(QWidget):
                if child.isWindow():
                    child.hide()
        except Exception as e:
            logging.error(f"Error hiding children in hideEvent: {e}")
        super().hideEvent(event)

    def update_geometry(self):
        if not self.video_widget or not self.video_widget.isVisible():
            self.hide()
            return

        self._check_install_window_filter()

        # Map video widget top-left to global screen coordinates
        global_pos = self.video_widget.mapToGlobal(QPoint(0, 0))
        vw = self.video_widget.width()
        vh = self.video_widget.height()

        # Determine if window is fullscreen
        is_fullscreen = False
        win = getattr(self, '_installed_window', None)
        if win:
            is_fullscreen = win.isFullScreen()
        elif self.player_window:
            is_fullscreen = self.player_window.window().isFullScreen()

        # Stretch from left to right edge of the video widget
        width = vw

        # Update the HTML if font size changes due to height change
        font_size = self.get_calculated_font_size()
        if hasattr(self, 'current_font_size') and self.current_font_size != font_size:
            self.current_font_size = font_size
            if self.current_text:
                html = f"""
                <div style="text-align: center; color: {self.text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {font_size}px; font-weight: normal; line-height: 1.2;">
                    {self.current_text}
                </div>
                """
                self.text_edit.setHtml(html)

        # Adjust text width in the document to compute wrap height
        text_width = width - 100  # Adjust for 50px left/right layout margins
        self.text_edit.document().setTextWidth(text_width)
        
        # Calculate dynamic height based on document content height
        doc_height = int(self.text_edit.document().size().height())
        height = max(50, doc_height + 20)  # padding/margins

        # Centered horizontally, positioned near the bottom
        x = global_pos.x()
        
        # Bottom margin adjustments
        bottom_margin = 15 if is_fullscreen else 10
        y = global_pos.y() + vh - height - bottom_margin

        self.setGeometry(x, y, width, height)

        # If the widget could not shrink to the requested height due to layout or OS constraints,
        # adjust y so that the bottom of the widget does not exceed the video widget bottom.
        actual_height = self.height()
        if actual_height > height:
            y = global_pos.y() + vh - actual_height - bottom_margin
            self.setGeometry(x, y, width, actual_height)

    def eventFilter(self, obj, event):
        if obj == self.video_widget:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show, QEvent.Type.Hide):
                self.update_geometry()
                if event.type() == QEvent.Type.Show:
                    if self._should_be_visible():
                        self.show()
                elif event.type() == QEvent.Type.Hide:
                    self.hide()
        elif hasattr(self, '_installed_window') and obj == self._installed_window:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self.update_geometry()
            elif event.type() == QEvent.Type.WindowStateChange:
                if self._installed_window.isMinimized():
                    self.hide()
                else:
                    QTimer.singleShot(0, self.update_visibility)
        elif obj == self.player_window:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self.update_geometry()
            elif event.type() == QEvent.Type.WindowStateChange:
                if self.player_window.isMinimized():
                    self.hide()
                else:
                    QTimer.singleShot(0, self.update_visibility)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        # Clean up event filters
        if self.video_widget:
            self.video_widget.removeEventFilter(self)
        if self.player_window:
            self.player_window.removeEventFilter(self)
        if hasattr(self, '_installed_window') and self._installed_window:
            try:
                self._installed_window.removeEventFilter(self)
            except Exception:
                pass
        super().closeEvent(event)
