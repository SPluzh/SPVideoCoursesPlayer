import string
import logging
from PyQt6.QtWidgets import QFrame, QTextEdit, QVBoxLayout, QApplication, QWidget, QSizePolicy, QPushButton
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
        self.setObjectName("subtitleTextEdit")

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

            pos = event.position().toPoint()

            # If user is selecting text (left button is down), do not trigger hover translation
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.hover_timer.stop()
                return

            # If there is already an active selection, do not trigger hover translation
            if self.textCursor().hasSelection():
                self.hover_timer.stop()
                return

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
                            
                            # Calculate top-center of the hovered word
                            start_cursor = QTextCursor(cursor)
                            start_cursor.setPosition(cursor.selectionStart())
                            end_cursor = QTextCursor(cursor)
                            end_cursor.setPosition(cursor.selectionEnd())
                            
                            r_start = self.cursorRect(start_cursor)
                            r_end = self.cursorRect(end_cursor)
                            
                            if abs(r_start.top() - r_end.top()) < 5:
                                x = (r_start.left() + r_end.left()) // 2
                            else:
                                x = r_start.left()
                            y = r_start.top()
                            
                            self.hover_pos = self.viewport().mapToGlobal(QPoint(x, y))
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
                    # Calculate top-center of the selected phrase
                    start_cursor = QTextCursor(cursor)
                    start_cursor.setPosition(cursor.selectionStart())
                    end_cursor = QTextCursor(cursor)
                    end_cursor.setPosition(cursor.selectionEnd())
                    
                    r_start = self.cursorRect(start_cursor)
                    r_end = self.cursorRect(end_cursor)
                    
                    if abs(r_start.top() - r_end.top()) < 5:
                        x = (r_start.left() + r_end.left()) // 2
                    else:
                        x = r_start.left()
                    y = r_start.top()
                    
                    global_pos = self.viewport().mapToGlobal(QPoint(x, y))
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
            self.viewport().setMouseTracking(True)
            parent = self.parent()
            if parent and hasattr(parent, "mouseEntered"):
                parent.mouseEntered.emit()
            super().enterEvent(event)
        except Exception as e:
            logging.error(f"Error in enterEvent: {e}", exc_info=True)


class SubtitleOverlayWidget(QFrame):
    mouseEntered = pyqtSignal()
    mouseLeft = pyqtSignal()
    translateRequested = pyqtSignal(str, QPoint)
    prevPhraseRequested = pyqtSignal()
    nextPhraseRequested = pyqtSignal()
    replayPhraseRequested = pyqtSignal()

    def __init__(self, video_widget, player_window):
        super().__init__(video_widget, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.video_widget = video_widget
        self.player_window = player_window
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setObjectName("SubtitleOverlayWidget")

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 8, 160, 8)
        layout.setSpacing(0)

        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        # Text Edit
        self.text_edit = SubtitleTextEdit(self)
        self.text_edit.document().setDocumentMargin(0)
        self.text_edit.setMinimumHeight(0)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.text_edit)

        # Secondary Text Edit
        self.secondary_text_edit = SubtitleTextEdit(self)
        self.secondary_text_edit.document().setDocumentMargin(0)
        self.secondary_text_edit.setMinimumHeight(0)
        self.secondary_text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.secondary_text_edit)
        self.secondary_text_edit.hide()

        # Translate entire subtitle button
        self.translate_btn = QPushButton(self)
        self.translate_btn.setObjectName("translateSubBtn")
        self.translate_btn.setFixedSize(30, 30)
        self.translate_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        from icon_manager import load_icon
        self.translate_btn.setIcon(load_icon("languages"))
        from translator import tr
        self.translate_btn.setToolTip(tr("translator.translate_subtitle"))
        self.translate_btn.clicked.connect(self._on_translate_btn_clicked)
        self.translate_btn.hide()

        # Previous subtitle phrase button
        self.prev_phrase_btn = QPushButton(self)
        self.prev_phrase_btn.setObjectName("prevPhraseBtn")
        self.prev_phrase_btn.setFixedSize(30, 30)
        self.prev_phrase_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_phrase_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_phrase_btn.setIcon(load_icon("prev_frame"))
        self.prev_phrase_btn.setToolTip(tr("translator.prev_phrase"))
        self.prev_phrase_btn.clicked.connect(self.prevPhraseRequested.emit)
        self.prev_phrase_btn.hide()

        # Next subtitle phrase button
        self.next_phrase_btn = QPushButton(self)
        self.next_phrase_btn.setObjectName("nextPhraseBtn")
        self.next_phrase_btn.setFixedSize(30, 30)
        self.next_phrase_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_phrase_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_phrase_btn.setIcon(load_icon("next_frame"))
        self.next_phrase_btn.setToolTip(tr("translator.next_phrase"))
        self.next_phrase_btn.clicked.connect(self.nextPhraseRequested.emit)
        self.next_phrase_btn.hide()

        # Replay current subtitle phrase button
        self.replay_phrase_btn = QPushButton(self)
        self.replay_phrase_btn.setObjectName("replayPhraseBtn")
        self.replay_phrase_btn.setFixedSize(30, 30)
        self.replay_phrase_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.replay_phrase_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.replay_phrase_btn.setIcon(load_icon("menu_reload"))
        self.replay_phrase_btn.setToolTip(tr("translator.replay_phrase"))
        self.replay_phrase_btn.clicked.connect(self.replayPhraseRequested.emit)
        self.replay_phrase_btn.hide()

        # Connect signals for showing/hiding translate button on hover
        self.mouseEntered.connect(self._show_translate_btn)
        self.mouseLeft.connect(self._hide_translate_btn)

        # Connect event filters to dynamically update geometry
        if self.video_widget:
            self.video_widget.installEventFilter(self)
        if self.player_window:
            self.player_window.installEventFilter(self)

        self.text_color = "#FFCC66"
        self.outline_color = "#000000"
        self.secondary_text_color = "#E6E6FA"
        self.font_scale = 1.0
        self.bg_opacity = 70
        self.current_text = ""
        self.secondary_text = ""
        self.current_font_size = 0
        self.secondary_hover_only = True
        self._is_hovered = False
        self._pip_transition = False

        self.update_geometry()
        # Deferred: install filter on the real QMainWindow once the widget
        # is fully embedded in the hierarchy (window() returns the root then).
        QTimer.singleShot(0, self._install_main_window_filter)

        # Application-level filter to detect when the user switches to another app
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

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

    def set_secondary_hover_only(self, enabled: bool):
        self.secondary_hover_only = enabled
        self._apply_secondary_visibility()

    def _should_secondary_be_visible(self) -> bool:
        if not self.secondary_text_edit.toPlainText().strip():
            return False
        if self.secondary_hover_only:
            is_over_overlay = False
            try:
                from PyQt6.QtGui import QCursor
                is_over_overlay = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
            except Exception:
                pass
            
            is_over_translation = False
            try:
                from PyQt6.QtGui import QCursor
                if self.player_window and hasattr(self.player_window, 'translation_popup'):
                    pop = self.player_window.translation_popup
                    if pop and pop.isVisible():
                        is_over_translation = pop.rect().contains(pop.mapFromGlobal(QCursor.pos()))
            except Exception:
                pass
                
            self._is_hovered = is_over_overlay or is_over_translation
            return self._is_hovered
        return True

    def _apply_secondary_visibility(self):
        """Show/hide secondary_text_edit based on hover_only flag and hover state."""
        should_visible = self._should_secondary_be_visible()
        is_visible = self.secondary_text_edit.isVisible()
        if should_visible != is_visible:
            if should_visible:
                self.secondary_text_edit.show()
            else:
                self.secondary_text_edit.hide()
            self.update_geometry()

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
        
        # Use user-defined outline_color as base, with alpha based on bg_opacity
        base_color = getattr(self, "outline_color", "#000000")
        bg_color = QColor(base_color)
        if not bg_color.isValid():
            bg_color = QColor(0, 0, 0)
        opacity = getattr(self, "bg_opacity", 70)
        alpha = int(opacity * 2.55)
        bg_color.setAlpha(alpha)
        
        painter.fillRect(self.rect(), bg_color)

    def _should_be_visible(self) -> bool:
        if not self.video_widget or not self.video_widget.isVisible():
            return False
        if not self.text_edit.toPlainText().strip() and not self.secondary_text_edit.toPlainText().strip():
            return False

        # Always resolve the real top-level window fresh (never trust stale cache).
        # After PiP setWindowFlags() the HWND is recreated, so video_widget.window()
        # may return a different object than _installed_window.
        win = None
        if self.video_widget:
            win = self.video_widget.window()
        if not win and self.player_window:
            win = self.player_window.window()

        # If the top-level window changed (e.g. after PiP flag switch), silently
        # reinstall the event filter so future visibility checks work correctly.
        if win and getattr(self, '_installed_window', None) is not win:
            self.reinstall_window_filter()

        if win and win.isMinimized():
            return False

        return True

    def _is_any_popup_visible(self) -> bool:
        if self.player_window:
            if hasattr(self.player_window, 'subtitle_btn'):
                btn = self.player_window.subtitle_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    return True
            if hasattr(self.player_window, 'volume_btn'):
                btn = self.player_window.volume_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    return True
        return False

    def update_visibility(self):
        try:
            if self._should_be_visible():
                self.show()
                if not self._is_any_popup_visible():
                    self.raise_()
            else:
                self.hide()
        except Exception as e:
            logging.error(f"Error updating visibility: {e}", exc_info=True)

    def set_text(self, text):
        self.current_text = text
        if not text:
            self.text_edit.clear()
            if not self.secondary_text_edit.toPlainText().strip():
                if hasattr(self, 'translate_btn') and self.translate_btn:
                    self.translate_btn.hide()
                if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
                    self.prev_phrase_btn.hide()
                if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
                    self.next_phrase_btn.hide()
                self.hide()
                return
        else:
            # Render centered text
            font_size = self.get_calculated_font_size()
            self.current_font_size = font_size
            html = f"""
            <div style="text-align: center; color: {self.text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {font_size}px; font-weight: normal; line-height: 1.0;">
                {text}
            </div>
            """
            self.text_edit.setHtml(html)
        
        # Ensure geometry is updated for the new text
        self.update_geometry()
        
        # Check hover to show/hide translate button
        from PyQt6.QtGui import QCursor
        try:
            is_hovered = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
            if is_hovered:
                self._show_translate_btn()
            else:
                self._hide_translate_btn()
        except Exception:
            pass

        # Check visibility conditions
        if self._should_be_visible():
            self.show()
            # Raise overlay to ensure it's on top of any video surface
            if not self._is_any_popup_visible():
                self.raise_()
        else:
            self.hide()

    def set_secondary_text(self, text):
        self.secondary_text = text
        if not text:
            self.secondary_text_edit.clear()
            if not self.text_edit.toPlainText().strip():
                if hasattr(self, 'translate_btn') and self.translate_btn:
                    self.translate_btn.hide()
                if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
                    self.prev_phrase_btn.hide()
                if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
                    self.next_phrase_btn.hide()
                self.hide()
                return
        else:
            # Render centered secondary text with configured color and 85% font size
            font_size = int(self.get_calculated_font_size() * 0.85)
            text_color = getattr(self, "secondary_text_color", "#E6E6FA")
            html = f"""
            <div style="text-align: center; color: {text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {font_size}px; font-weight: normal; line-height: 1.0;">
                {text}
            </div>
            """
            self.secondary_text_edit.setHtml(html)
        
        self.update_geometry()
        
        # Check hover to show/hide translate button
        from PyQt6.QtGui import QCursor
        try:
            is_hovered = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
            if is_hovered:
                self._show_translate_btn()
            else:
                self._hide_translate_btn()
        except Exception:
            pass

        if self._should_be_visible():
            self.show()
            if not self._is_any_popup_visible():
                self.raise_()
        else:
            self.hide()

    def set_subtitle_style(self, text_color, outline_color, font_scale, secondary_text_color=None, bg_opacity=None):
        self.text_color = text_color
        self.outline_color = outline_color
        self.font_scale = font_scale
        if secondary_text_color is not None:
            self.secondary_text_color = secondary_text_color
        if bg_opacity is not None:
            self.bg_opacity = bg_opacity
        # Refresh current text if any
        self.set_text(self.current_text)
        if getattr(self, 'secondary_text', None):
            self.set_secondary_text(self.secondary_text)
        self.update()

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

    def _install_main_window_filter(self):
        """Find the true top-level QMainWindow and install an event filter on it.
        Called deferred (via QTimer.singleShot) so the widget hierarchy is fully
        built and video_widget.window() returns the real root window.
        """
        win = None
        if self.video_widget:
            win = self.video_widget.window()
        elif self.player_window:
            win = self.player_window.window()

        if not win:
            return

        # Already installed on this window — nothing to do
        if getattr(self, '_installed_window', None) is win:
            return

        # Remove filter from the old window if present
        old_win = getattr(self, '_installed_window', None)
        if old_win:
            try:
                old_win.removeEventFilter(self)
            except Exception:
                pass

        win.installEventFilter(self)
        self._installed_window = win
        logging.debug(f"SubtitleOverlay: event filter installed on {win!r}")

    def reinstall_window_filter(self):
        """Re-attach the event filter to the current top-level window.

        Must be called after any setWindowFlags() call that recreates the HWND,
        such as entering or exiting PiP mode. The old _installed_window reference
        becomes stale after flag changes, causing isActiveWindow() to return False
        and breaking hover highlight / translation popup.
        """
        try:
            win = None
            if self.video_widget:
                win = self.video_widget.window()
            elif self.player_window:
                win = self.player_window.window()

            if not win:
                return

            old_win = getattr(self, '_installed_window', None)
            if old_win is not win:
                # Remove filter from the stale window (may already be invalid)
                if old_win:
                    try:
                        old_win.removeEventFilter(self)
                    except Exception:
                        pass
                self._installed_window = None

                # Install on the fresh window
                win.installEventFilter(self)
                self._installed_window = win
                logging.debug(f"SubtitleOverlay: reinstalled event filter on {win!r}")
        except Exception as e:
            logging.error(f"SubtitleOverlay.reinstall_window_filter: {e}", exc_info=True)

    def reattach_to_video_widget(self):
        """Re-bind the overlay to the video_widget's native parent after PiP.

        When setWindowFlags() is called on the main window (enter/exit PiP mode),
        Qt recreates the native HWND for the entire window hierarchy. The ToolTip-type
        overlay (SubtitleOverlayWidget) loses its native parent binding and stops
        receiving mouse events (enterEvent / leaveEvent / mouseMoveEvent all break).

        Calling setParent() + setWindowFlags() + show() forces Qt to create a new
        native ToolTip window attached to the current (fresh) native parent of
        video_widget. After this, mouse tracking is fully restored.
        """
        try:
            if not self.video_widget:
                return

            self._pip_transition = True
            QTimer.singleShot(600, self._clear_pip_transition)

            was_visible = self.isVisible()

            # Temporarily hide to avoid visual glitch during reparenting
            super().hide()

            # Re-attach: setParent resets window flags, so we must set them again
            self.setParent(self.video_widget)
            self.setWindowFlags(
                Qt.WindowType.ToolTip
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.NoDropShadowWindowHint
            )

            # Restore WA attributes that setParent may clear
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

            # Reinstall event filter on the fresh top-level window
            self.reinstall_window_filter()

            # Recompute geometry and restore visibility
            self.update_geometry()
            if was_visible:
                self.update_visibility()

            # Clear any stale text selection/hover state from PiP mode
            for edit in (self.text_edit, self.secondary_text_edit):
                try:
                    cursor = edit.textCursor()
                    if cursor.hasSelection():
                        cursor.clearSelection()
                        edit.setTextCursor(cursor)
                    edit.hover_timer.stop()
                    edit.current_hovered_word = ""
                    edit.current_hovered_cursor = None
                    edit.setExtraSelections([])
                except Exception:
                    pass

            # Explicitly restore mouse tracking properties
            self.setMouseTracking(True)
            self.text_edit.setMouseTracking(True)
            self.text_edit.viewport().setMouseTracking(True)
            self.secondary_text_edit.setMouseTracking(True)
            self.secondary_text_edit.viewport().setMouseTracking(True)

            # Deferred pass — ensure OS-level tracking is active after Qt processes show events
            QTimer.singleShot(100, self._restore_viewport_tracking)

            logging.debug("SubtitleOverlay: reattached to video_widget native parent")
        except Exception as e:
            logging.error(f"SubtitleOverlay.reattach_to_video_widget: {e}", exc_info=True)

    def _restore_viewport_tracking(self):
        """Re-apply mouse tracking on viewports after deferred HWND creation."""
        try:
            for edit in (self.text_edit, self.secondary_text_edit):
                edit.setMouseTracking(True)
                edit.viewport().setMouseTracking(True)
            self.setMouseTracking(True)
        except Exception as e:
            logging.error(f"SubtitleOverlay._restore_viewport_tracking: {e}", exc_info=True)

    def _clear_pip_transition(self):
        self._pip_transition = False
        self.update_visibility()

    def show(self):
        super().show()
        if self.player_window:
            if hasattr(self.player_window, 'subtitle_btn'):
                btn = self.player_window.subtitle_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    btn.popup.raise_()
            if hasattr(self.player_window, 'volume_btn'):
                btn = self.player_window.volume_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    btn.popup.raise_()

    def showEvent(self, event):
        self._check_install_window_filter()
        super().showEvent(event)
        if self.player_window:
            if hasattr(self.player_window, 'subtitle_btn'):
                btn = self.player_window.subtitle_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    btn.popup.raise_()
            if hasattr(self.player_window, 'volume_btn'):
                btn = self.player_window.volume_btn
                if btn and hasattr(btn, 'popup') and btn.popup and btn.popup.isVisible():
                    btn.popup.raise_()

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
                <div style="text-align: center; color: {self.text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {font_size}px; font-weight: normal; line-height: 1.0;">
                    {self.current_text}
                </div>
                """
                self.text_edit.setHtml(html)
            if getattr(self, 'secondary_text', None):
                sec_font_size = int(font_size * 0.85)
                sec_html = f"""
                <div style="text-align: center; color: {self.secondary_text_color}; font-family: 'Segoe UI', Arial, sans-serif; font-size: {sec_font_size}px; font-weight: normal; line-height: 1.0;">
                    {self.secondary_text}
                </div>
                """
                self.secondary_text_edit.setHtml(sec_html)

        # Adjust text width in the document to compute wrap height
        text_width = width - 185  # Adjust for left (25px) and right (160px) margins
        
        primary_height = 0
        secondary_height = 0
        if self.text_edit.toPlainText().strip():
            self.text_edit.document().setTextWidth(text_width)
            primary_height = int(self.text_edit.document().size().height())
            self.text_edit.setFixedHeight(primary_height)
            self.text_edit.show()
        else:
            self.text_edit.hide()

        if self._should_secondary_be_visible():
            self.secondary_text_edit.document().setTextWidth(text_width)
            secondary_height = int(self.secondary_text_edit.document().size().height())
            self.secondary_text_edit.setFixedHeight(secondary_height)
            self.secondary_text_edit.show()
        else:
            self.secondary_text_edit.hide()

        doc_height = primary_height + secondary_height
        layout = self.layout()
        if primary_height > 0 and secondary_height > 0:
            doc_height += 4
            layout.setSpacing(4)
        else:
            layout.setSpacing(0)

        # Height is doc_height + top_margin(8) + bottom_margin(8)
        height = doc_height + 16

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

        # Position buttons at the right side of the widget
        actual_height = self.height()
        btn_width = 30
        btn_height = 30
        btn_y = (actual_height - btn_height) // 2

        # next_phrase_btn is placed at the far right
        if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
            btn_x = width - btn_width - 10
            self.next_phrase_btn.setGeometry(btn_x, btn_y, btn_width, btn_height)

        # translate_btn is placed to the left of next_phrase_btn
        if hasattr(self, 'translate_btn') and self.translate_btn:
            btn_x = width - btn_width - 10 - btn_width - 5  # 5px spacing
            self.translate_btn.setGeometry(btn_x, btn_y, btn_width, btn_height)

        # replay_phrase_btn is placed to the left of translate_btn
        if hasattr(self, 'replay_phrase_btn') and self.replay_phrase_btn:
            btn_x = width - btn_width - 10 - 2 * (btn_width + 5)  # 5px spacing
            self.replay_phrase_btn.setGeometry(btn_x, btn_y, btn_width, btn_height)

        # prev_phrase_btn is placed to the left of replay_phrase_btn
        if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
            btn_x = width - btn_width - 10 - 3 * (btn_width + 5)  # 5px spacing
            self.prev_phrase_btn.setGeometry(btn_x, btn_y, btn_width, btn_height)

    def _show_translate_btn(self):
        self._is_hovered = True
        self._apply_secondary_visibility()
        if self.current_text:
            if hasattr(self, 'translate_btn') and self.translate_btn:
                self.translate_btn.show()
            if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
                self.prev_phrase_btn.show()
            if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
                self.next_phrase_btn.show()
            if hasattr(self, 'replay_phrase_btn') and self.replay_phrase_btn:
                self.replay_phrase_btn.show()

    def _hide_translate_btn(self):
        self._is_hovered = False
        self._apply_secondary_visibility()
        if hasattr(self, 'translate_btn') and self.translate_btn:
            self.translate_btn.hide()
        if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
            self.prev_phrase_btn.hide()
        if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
            self.next_phrase_btn.hide()
        if hasattr(self, 'replay_phrase_btn') and self.replay_phrase_btn:
            self.replay_phrase_btn.hide()

    def update_texts(self):
        from translator import tr
        if hasattr(self, 'translate_btn') and self.translate_btn:
            self.translate_btn.setToolTip(tr("translator.translate_subtitle"))
        if hasattr(self, 'prev_phrase_btn') and self.prev_phrase_btn:
            self.prev_phrase_btn.setToolTip(tr("translator.prev_phrase"))
        if hasattr(self, 'next_phrase_btn') and self.next_phrase_btn:
            self.next_phrase_btn.setToolTip(tr("translator.next_phrase"))
        if hasattr(self, 'replay_phrase_btn') and self.replay_phrase_btn:
            self.replay_phrase_btn.setToolTip(tr("translator.replay_phrase"))

    def trigger_translation(self):
        """Programmatically trigger translation of the current subtitle text."""
        self._on_translate_btn_clicked()

    def _on_translate_btn_clicked(self):
        try:
            if not self.current_text:
                return
            center_x = self.mapToGlobal(QPoint(self.width() // 2, 0)).x()
            top_y = self.mapToGlobal(QPoint(0, 0)).y()
            anchor_pos = QPoint(center_x, top_y)
            self.translateRequested.emit(self.current_text, anchor_pos)
        except Exception as e:
            logging.error(f"Error in _on_translate_btn_clicked: {e}", exc_info=True)

    def eventFilter(self, obj, event):
        if obj is QApplication.instance():
            if event.type() == QEvent.Type.ApplicationDeactivate:
                # User switched to another OS application entirely — hide overlay
                self.hide()
            elif event.type() == QEvent.Type.ApplicationActivate:
                # User switched back — re-evaluate visibility after a short delay
                # (window activation state may not be updated yet)
                QTimer.singleShot(200, self.update_visibility)
            return False
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
                    # Small delay: window is still animating back from minimized state
                    QTimer.singleShot(150, self.update_visibility)
        elif obj == self.player_window:
            # player_window is a QWidget (VideoPlayerWidget), NOT a QWindow —
            # WindowStateChange is never emitted by it, so handle only geometry.
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self.update_geometry()
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
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self)
        super().closeEvent(event)
