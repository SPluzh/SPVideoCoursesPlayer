from pathlib import Path
import logging

from PyQt6.QtWidgets import QTreeWidget, QStyledItemDelegate, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QRectF, QPointF, QEvent
from PyQt6.QtGui import (
    QAction, QColor, QIcon, QPainter, QPixmap, QPalette, QBrush, 
    QStandardItem, QFont, QPen, QFontMetrics, QPainterPath, QTextLayout, QTextOption,
    QPolygon
)

from translator import tr
from placeholders import draw_library_placeholder
from video_item_data import VideoItemData

class VideoItemDelegate(QStyledItemDelegate):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_thumbnail_index = 0
        self.hovered_index = None
        self.thumbnail_cache = {}
        self.playing_path = None
        self.is_paused = True
        self.mouse_pos = None
        self._init_style_widgets()

    def _init_style_widgets(self):
        """Create widgets to retrieve styles from QSS."""
        self.thumbnail_border = QWidget()
        self.thumbnail_border.setObjectName("thumbnail_border")

        self.progress_bar_bg = QWidget()
        self.progress_bar_bg.setObjectName("progress_bar_bg")

        self.progress_bar_fill = QWidget()
        self.progress_bar_fill.setObjectName("progress_bar_fill")

        self.dot_active = QWidget()
        self.dot_active.setObjectName("dot_active")

        self.dot_inactive = QWidget()
        self.dot_inactive.setObjectName("dot_inactive")

        self.empty_thumbnail_bg = QWidget()
        self.empty_thumbnail_bg.setObjectName("empty_thumbnail_bg")

        self.empty_thumbnail_border = QWidget()
        self.empty_thumbnail_border.setObjectName("empty_thumbnail_border")

        self.empty_thumbnail_icon = QLabel()
        self.empty_thumbnail_icon.setObjectName("empty_thumbnail_icon")

        self.duration_label_bg = QWidget()
        self.duration_label_bg.setObjectName("duration_label_bg")

        self.duration_label_text = QLabel()
        self.duration_label_text.setObjectName("duration_label_text")

        self.video_title = QLabel()
        self.video_title.setObjectName("video_title")

        self.video_info = QLabel()
        self.video_info.setObjectName("video_info")

        self.video_progress_text = QLabel()
        self.video_progress_text.setObjectName("video_progress_text")

        self.row_play_button_bg = QWidget()
        self.row_play_button_bg.setObjectName("row_play_button_bg")

        self.row_play_button_icon = QLabel()
        self.row_play_button_icon.setObjectName("row_play_button_icon")

        all_widgets = [
            self.thumbnail_border, self.progress_bar_bg, self.progress_bar_fill,
            self.dot_active, self.dot_inactive, self.empty_thumbnail_bg,
            self.empty_thumbnail_border, self.empty_thumbnail_icon,
            self.duration_label_bg, self.duration_label_text,
            self.video_title, self.video_info, self.video_progress_text,
            self.row_play_button_bg, self.row_play_button_icon
        ]
        for widget in all_widgets:
            widget.ensurePolished()

    def set_hovered_index(self, index, thumbnail_index=0, mouse_pos=None):
        self.hovered_index = index
        self.current_thumbnail_index = thumbnail_index
        self.mouse_pos = mouse_pos

    def get_play_button_rect(self, rect):
        """Return Play button area on thumbnail."""
        try:
            display_width = self.config['display_width']
            display_height = self.config['display_height']
            
            # Sync with paint() logic: centered vertically in base row height
            base_height = self.config['video_row_height']
            thumb_y = rect.top() + (base_height - display_height) // 2
            thumb_rect = QRect(rect.left() - 15, thumb_y,
                              display_width, display_height)
            
            btn_size = 28 # Slightly smaller for corner
            margin = 2
            return QRect(
                thumb_rect.right() - btn_size - margin,
                thumb_rect.top() + margin,
                btn_size, btn_size
            )
        except Exception as e:
            logging.error(f"Error in get_play_button_rect: {e}")
            return QRect()

    def sizeHint(self, option, index):
        try:
            # import sys; sys.stderr.write(f"[SIZEHINT] row={index.row()}\n"); sys.stderr.flush()
            size = super().sizeHint(option, index)
            item_type = index.data(Qt.ItemDataRole.UserRole + 1)
            if item_type == 'folder':
                size.setHeight(self.config['folder_row_height'])
            elif item_type == 'video':
                base_height = self.config['video_row_height']
                
                # Check for markers to increase height
                data = index.data(Qt.ItemDataRole.UserRole + 2)
                marker_height = 0
                show_markers = self.config.get('show_markers', True)
                if show_markers and data and isinstance(data, VideoItemData) and getattr(data, 'markers', None):
                    # 20px per marker line
                    marker_height = len(data.markers) * 20 + 4 # 4px padding
                    
                size.setHeight(base_height + marker_height)
                
            return size
        except Exception as e:
            logging.error(f"Error in sizeHint: {e}")
            return super().sizeHint(option, index)

    def _get_pixmap(self, path):
        if path not in self.thumbnail_cache:
            if path and Path(path).exists():
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.thumbnail_cache[path] = pixmap
                else:
                    self.thumbnail_cache[path] = None
            else:
                self.thumbnail_cache[path] = None
        return self.thumbnail_cache.get(path)

    def paint(self, painter, option, index): # Overridden
        # Recursion guard - prevent re-entrant paint calls
        if getattr(self, '_paint_in_progress', False):
            return
        self._paint_in_progress = True
        try:
            if not index.isValid():
                return

            item_type = index.data(Qt.ItemDataRole.UserRole + 1)
            
            # Handle Folder Rendering
            if item_type == 'folder':
                self.paint_folder(painter, option, index)
                return

            if item_type != 'video':
                super().paint(painter, option, index)
                return

            painter.save()
            data = index.data(Qt.ItemDataRole.UserRole + 2)
            if not data:
                painter.restore()
                return

            # Unpack data
            if isinstance(data, VideoItemData):
                filename = data.filename
                duration = data.duration
                resolution = data.resolution
                file_size = data.file_size
                watched_percent = data.watched_percent
                thumbnail_path = data.thumbnail_path
                thumbnails_list = getattr(data, 'thumbnails_list', []) or []
                last_position = data.last_position
                marker_count = data.marker_count
                is_favorite = data.is_favorite
                tags = getattr(data, 'tags', []) or []
                markers = getattr(data, 'markers', []) or []
            else:
                # Fallback for old data or tuple/list
                markers = []
                tags = []
                thumbnails_list = []
                if isinstance(data, (tuple, list)) and len(data) >= 9:
                    filename, duration, resolution, file_size, watched_percent, thumbnail_path, thumbnails_list, last_position, marker_count = data[:9]
                    is_favorite = 0
                else:
                    painter.restore()
                    return

            display_width = self.config['display_width']
            display_height = self.config['display_height']

            # If we are effectively "under" the main row content, we should standardise top alignment for main content
            # But sizeHint logic: size.setHeight(base_height + marker_height)
            # So the "main" part (thumb + text) is in the first `base_height` pixels.
            # We should recalculate thumb_y to be centered in that base_height, or fixed top offset.
            # Current logic centers it in the FULL rect height which includes markers. This is WRONG if markers are huge.
            # We want thumb to stay at top.
            
            base_height = self.config['video_row_height']
            thumb_y = option.rect.top() + (base_height - display_height) // 2
            
            thumb_rect = QRect(option.rect.left() - 15, thumb_y,
                              display_width, display_height)

            current_thumb = thumbnail_path
            if self.hovered_index is not None and self.hovered_index == index and thumbnails_list:
                thumb_index = self.current_thumbnail_index % len(thumbnails_list)
                current_thumb = thumbnails_list[thumb_index]

            pixmap = self._get_pixmap(current_thumb)
            if pixmap:
                scaled_pixmap = pixmap.scaled(
                    display_width, display_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                x_offset = (display_width - scaled_pixmap.width()) // 2
                y_offset = (display_height - scaled_pixmap.height()) // 2
                
                path = QPainterPath()
                path.addRoundedRect(QRectF(thumb_rect), 3.0, 3.0)
                painter.save()
                painter.setClipPath(path)
                painter.drawPixmap(thumb_rect.left() + x_offset, thumb_rect.top() + y_offset, scaled_pixmap)
                painter.restore()

                playing_file = index.data(Qt.ItemDataRole.UserRole)
                if self.playing_path and playing_file == self.playing_path:
                    pen = QPen(QColor(1, 133, 116), 8)
                    painter.setPen(pen)
                    painter.drawRoundedRect(thumb_rect.adjusted(-4, -4, 4, 4), 7, 7)
                else:
                    painter.setPen(self.thumbnail_border.palette().color(QPalette.ColorRole.Mid))
                    painter.drawRoundedRect(thumb_rect, 3, 3)

                if last_position > 0 and duration > 0:
                    progress_percent = (last_position / duration) * 100
                    progress_bar_height = self.progress_bar_bg.minimumHeight() or 5
                    progress_bar_y = thumb_rect.bottom() - progress_bar_height - 1
                    progress_bar_rect = QRect(thumb_rect.left() + 1, progress_bar_y,
                                             display_width - 2, progress_bar_height)
                    painter.fillRect(progress_bar_rect, self.progress_bar_bg.palette().color(QPalette.ColorRole.Window))
                    filled_width = int((display_width - 2) * progress_percent / 100)
                    if filled_width > 0:
                        filled_rect = QRect(progress_bar_rect.left(), progress_bar_rect.top(),
                                          filled_width, progress_bar_height)
                        painter.fillRect(filled_rect, self.progress_bar_fill.palette().color(QPalette.ColorRole.Window))

                if self.hovered_index is not None and self.hovered_index == index and thumbnails_list:
                    dot_y = thumb_rect.top() + 8
                    dot_width = 6
                    dot_spacing = 2
                    total_dots_width = dot_width * len(thumbnails_list) + (len(thumbnails_list) - 1) * dot_spacing
                    start_x = thumb_rect.left() + (display_width - total_dots_width) // 2
                    for i in range(len(thumbnails_list)):
                        dot_x = start_x + i * (dot_width + dot_spacing)
                        if i == self.current_thumbnail_index % len(thumbnails_list):
                            painter.setBrush(self.dot_active.palette().color(QPalette.ColorRole.Window))
                        else:
                            painter.setBrush(self.dot_inactive.palette().color(QPalette.ColorRole.Window))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(dot_x, dot_y, dot_width, dot_width)
            else:
                painter.fillRect(thumb_rect, self.empty_thumbnail_bg.palette().color(QPalette.ColorRole.Window))
                painter.setPen(self.empty_thumbnail_border.palette().color(QPalette.ColorRole.Mid))
                painter.drawRoundedRect(thumb_rect, 3, 3)
                painter.setPen(self.empty_thumbnail_icon.palette().color(QPalette.ColorRole.WindowText))
                painter.setFont(self.empty_thumbnail_icon.font())
                painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "\U0001f3ac")

            if is_favorite:
                painter.save()
                heart_size = 24
                heart_rect = QRect(thumb_rect.left() - 6, thumb_rect.top() - 6, heart_size, heart_size)
                font = painter.font(); font.setPointSize(20); painter.setFont(font)
                painter.setPen(QColor(0, 0, 0, 200))
                painter.drawText(heart_rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, "\u2665")
                painter.setPen(QColor('#e74c3c'))
                painter.drawText(heart_rect, Qt.AlignmentFlag.AlignCenter, "\u2665")
                painter.restore()

            if duration:
                duration_str = self.config['format_duration'](duration)
                painter.setFont(self.duration_label_text.font())
                text_rect = painter.fontMetrics().boundingRect(duration_str)
                bg_rect = QRect(thumb_rect.right() - text_rect.width() - 8,
                              thumb_rect.bottom() - text_rect.height() - 10,
                              text_rect.width() + 6, text_rect.height() + 4)
                painter.setBrush(self.duration_label_bg.palette().color(QPalette.ColorRole.Window))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 2, 2)
                painter.setPen(self.duration_label_text.palette().color(QPalette.ColorRole.WindowText))
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, duration_str)

            text_x = thumb_rect.right() + 12
            text_y = option.rect.top() + 8
            
            # NOTE: available_width must be calculated carefully to avoid negative values
            available_width = max(1, option.rect.right() - text_x - 10)

            painter.setFont(self.video_title.font())
            painter.setPen(self.video_title.palette().color(QPalette.ColorRole.WindowText))
            elided_name = painter.fontMetrics().elidedText(str(filename), Qt.TextElideMode.ElideRight, available_width)
            painter.drawText(QRect(text_x, text_y, available_width, 25), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_name)
            text_y += 25

            info_parts = []
            if resolution: info_parts.append(str(resolution))
            if file_size: info_parts.append(self.config['format_size'](file_size))
            if marker_count: info_parts.append(tr('video_info.markers', count=marker_count))

            if info_parts:
                painter.setFont(self.video_info.font())
                painter.setPen(self.video_info.palette().color(QPalette.ColorRole.WindowText))
                info_str = " \u2022 ".join(info_parts)
                painter.drawText(QRect(text_x, text_y, available_width, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, info_str)
                text_y += 20

            if watched_percent > 0 or last_position > 0:
                painter.setFont(self.video_progress_text.font())
                painter.setPen(self.video_progress_text.palette().color(QPalette.ColorRole.WindowText))
                if watched_percent == 100:
                    prog_text = tr('video_info.watched_label')
                elif last_position > 0 and duration > 0:
                    prog_text = tr('video_info.progress', position=self.config['format_duration'](last_position), total=self.config['format_duration'](duration))
                else:
                    prog_text = tr('video_info.progress_percent', percent=watched_percent)
                painter.drawText(QRect(text_x, text_y, available_width, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, prog_text)
                text_y += 20

            if tags:
                tag_x = text_x; tag_y = text_y + 2; tag_height = 18
                painter.save()
                font = painter.font(); font.setPointSize(8); font.setBold(True); painter.setFont(font)
                for tag in tags:
                    name = str(tag.get('name', ''))
                    color = QColor(tag.get('color') or '#3498db')
                    tag_width = painter.fontMetrics().horizontalAdvance(name) + 12
                    if tag_x + tag_width > option.rect.right(): break
                    tag_rect = QRect(tag_x, tag_y, tag_width, tag_height)
                    painter.setBrush(color); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(tag_rect, 6, 6)
                    painter.setPen(QColor('#ffffff')); painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, name)
                    tag_x += tag_width + 6
                painter.restore()
                # text_y += 20 # removed increment since markers are now separate

            is_playing_item = (self.playing_path and index.data(Qt.ItemDataRole.UserRole) == self.playing_path)
            if self.hovered_index == index or is_playing_item:
                play_btn_rect = self.get_play_button_rect(option.rect)
                
                is_over_btn = False
                if self.mouse_pos and play_btn_rect.contains(self.mouse_pos):
                    is_over_btn = True

                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                painter.setBrush(self.row_play_button_bg.palette().color(QPalette.ColorRole.Window))
                
                if not is_over_btn and self.hovered_index != index:
                     color = self.row_play_button_bg.palette().color(QPalette.ColorRole.Window)
                     color.setAlpha(150)
                     painter.setBrush(color)
                elif is_over_btn:
                    color = self.row_play_button_bg.palette().color(QPalette.ColorRole.Window)
                    painter.setBrush(color.lighter(110))
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(play_btn_rect, 3, 3)

                icon_color = self.row_play_button_icon.palette().color(QPalette.ColorRole.WindowText)
                painter.setBrush(icon_color)
                painter.setPen(Qt.PenStyle.NoPen)

                if is_playing_item and not self.is_paused:
                    bar_w = 4; bar_h = 14; gap = 4
                    center = play_btn_rect.center() + QPoint(1, 1)
                    rect1 = QRect(center.x() - bar_w - gap // 2, center.y() - bar_h // 2, bar_w, bar_h)
                    rect2 = QRect(center.x() + gap // 2, center.y() - bar_h // 2, bar_w, bar_h)
                    painter.drawRect(rect1)
                    painter.drawRect(rect2)
                else:
                    tri_w = 12; tri_h = 14
                    center = play_btn_rect.center() + QPoint(1, 1)
                    triangle = QPolygon([
                        QPoint(center.x() - tri_w // 2, center.y() - tri_h // 2),
                        QPoint(center.x() + tri_w // 2, center.y()),
                        QPoint(center.x() - tri_w // 2, center.y() + tri_h // 2)
                    ])
                    painter.drawPolygon(triangle)
                
            # Markers under thumbnail
            show_markers = self.config.get('show_markers', True)
            if show_markers and markers:
                # Align with thumbnail left
                marker_x = thumb_rect.left()
                # Start below the base height (thumb + text block)
                marker_y = option.rect.top() + self.config['video_row_height'] 
                marker_height = 18
                
                painter.save()
                font = painter.font(); font.setPointSize(9); painter.setFont(font)
                
                # Full width for markers? or limited?
                # "под картинкой" -> under picture. Let's start at thumb left, 
                # but allow width to extend to right edge (minus margin)
                marker_area_width = max(1, option.rect.right() - marker_x - 10)
                
                for marker in markers:
                    if marker_y > option.rect.bottom(): break
                    try: time_str = self.config['format_duration'](marker['position_seconds'])
                    except: time_str = "00:00"
                    label = str(marker.get('label', ''))
                    display_text = f"[{time_str}] {label}"
                    stripe_color = QColor(marker.get('color', '#3498db') or '#3498db')
                    
                    painter.fillRect(QRect(marker_x, marker_y + 2, 4, marker_height - 4), stripe_color)
                    painter.setPen(QColor('#dddddd'))
                    
                    text_w = max(1, marker_area_width - 16)
                    elided = painter.fontMetrics().elidedText(display_text, Qt.TextElideMode.ElideRight, text_w)
                    painter.drawText(QRect(marker_x + 16, marker_y, text_w, marker_height), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
                    marker_y += 20
                painter.restore()

            painter.restore()
            try: painter.restore()
            except: pass
        finally:
            self._paint_in_progress = False

    def get_marker_at_pos(self, rect, pos, index):
        """Check if position is over a marker."""
        data = index.data(Qt.ItemDataRole.UserRole + 2)
        markers = []
        if isinstance(data, VideoItemData):
            markers = getattr(data, 'markers', []) or []
        
        show_markers = self.config.get('show_markers', True)
        if show_markers and markers:
            base_height = self.config['video_row_height']
            
            # Match paint logic
            marker_x = rect.left()
            marker_y = rect.top() + base_height
            marker_height = 18
            
            for marker in markers:
                # Full width hit area
                available_width = rect.right() - marker_x - 10
                marker_rect = QRect(marker_x, marker_y, available_width, marker_height)
                
                if marker_rect.contains(pos):
                    return marker
                
                marker_y += 20
        return None

    def editorEvent(self, event, model, option, index):
        try:
            if event.type() == QEvent.Type.MouseButtonRelease:
                marker = self.get_marker_at_pos(option.rect, event.pos(), index)
                if marker:
                    file_path = index.data(Qt.ItemDataRole.UserRole)
                    pos = marker['position_seconds']
                    tree = self.parent()
                    if tree:
                            window = tree.window()
                            if hasattr(window, 'play_video_at_marker'):
                                window.play_video_at_marker(file_path, pos)
                    return True
                        
            return super().editorEvent(event, model, option, index)
        except Exception as e:
            logging.error(f"Error in editorEvent: {e}", exc_info=True)
            return False

    def paint_folder(self, painter, option, index):
        """Paint folder item with custom 16:9 icon."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Config dimensions
        video_height = self.config.get('video_row_height', 110)
        
        
        # Icon Area
        config = self.config
        # Reserve space for progress bar (8px + 2px padding + bottom padding)
        # So we subtract more from row height
        icon_height = config.get('folder_row_height', 70) - 14  
        icon_width = int(icon_height * 16 / 9)
        
        # Center vertically but shift up slightly to make room below?
        # Or just use row height logic.
        # If we reduce height by 14, we have 7px top/bottom padding if centered.
        # We need 2 (gap) + 8 (bar) = 10px below.
        # So shift up by 3px.
        
        center_y = option.rect.center().y()
        icon_rect = QRectF(
            option.rect.left() + 5,
            center_y - icon_height / 2 - 2, # Shift up 2px
            icon_width,
            icon_height
        )

        # Draw Icon Background (for missing images or transparent ones)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cover_path = index.data(Qt.ItemDataRole.UserRole + 4) # Folder image path
        pixmap = self._get_pixmap(cover_path)
        
        if pixmap:
            # Check if it's the default folder icon
            is_default = "folder_cover.png" in str(cover_path)
            mode = Qt.AspectRatioMode.KeepAspectRatio if is_default else Qt.AspectRatioMode.KeepAspectRatioByExpanding
            
            scaled_pixmap = pixmap.scaled(
                int(icon_width), int(icon_height),
                mode,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the pixmap in the rect (for AspectRatio handling)
            px_x = icon_rect.x() + (icon_rect.width() - scaled_pixmap.width()) / 2
            px_y = icon_rect.y() + (icon_rect.height() - scaled_pixmap.height()) / 2
            
            painter.drawPixmap(int(px_x), int(px_y), scaled_pixmap)
            
            # Draw border
            painter.setClipping(False) # Turn off clip for border
            painter.setPen(self.thumbnail_border.palette().color(QPalette.ColorRole.Mid))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(icon_rect, 3, 3)

            # Draw green stripe if folder contains currently playing video
            folder_path = index.data(Qt.ItemDataRole.UserRole)
            root_path = index.data(Qt.ItemDataRole.UserRole + 3)
            if self.playing_path and folder_path and root_path:
                try:
                    full_folder_path = Path(root_path) / folder_path
                    is_parent = Path(self.playing_path).is_relative_to(full_folder_path)
                    if is_parent:
                        stripe_width = 8
                        stripe_rect = QRectF(
                            icon_rect.left() - stripe_width,
                            icon_rect.top(),
                            stripe_width,
                            icon_rect.height()
                        )
                        # Use QPainterPath for partial rounding (only left side)
                        path = QPainterPath()
                        radius = 3
                        # Start from top-right
                        path.moveTo(stripe_rect.right(), stripe_rect.top())
                        # Top edge to start of top-left arc
                        path.lineTo(stripe_rect.left() + radius, stripe_rect.top())
                        # Top-left arc (x, y, w, h, startAngle, spanAngle)
                        path.arcTo(stripe_rect.left(), stripe_rect.top(), 2*radius, 2*radius, 90, 90)
                        # Left edge to start of bottom-left arc
                        path.lineTo(stripe_rect.left(), stripe_rect.bottom() - radius)
                        # Bottom-left arc
                        path.arcTo(stripe_rect.left(), stripe_rect.bottom() - 2*radius, 2*radius, 2*radius, 180, 90)
                        # Bottom edge to bottom-right
                        path.lineTo(stripe_rect.right(), stripe_rect.bottom())
                        # Right edge back to start (closing path)
                        path.closeSubpath()
                        
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        painter.fillPath(path, QColor(1, 133, 116))
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                except (ValueError, Exception):
                    pass
            
        else:
            # Fallback if no image found (shouldn't happen if default is set)
            painter.fillRect(icon_rect, self.empty_thumbnail_bg.palette().color(QPalette.ColorRole.Window))
            painter.setPen(self.empty_thumbnail_border.palette().color(QPalette.ColorRole.Mid))
            painter.drawRoundedRect(icon_rect, 3, 3)

        # Draw Folder Progress Bar
        progress = index.data(Qt.ItemDataRole.UserRole + 6)
        if progress is not None:
            # Always draw background/track if we moved layout, or only if > 0?
            # User said: "draw not on picture but under it"
            # And "make line height 2 times higher" -> 8px
            
            bar_height = 8
            gap = 2
            bar_y = icon_rect.bottom() + gap
            
            # Background
            bg_rect = QRectF(icon_rect.left(), bar_y, icon_rect.width(), bar_height)
            painter.fillRect(bg_rect, QColor(40, 40, 40)) # Dark track
            
            val = int(progress)
            if val > 0:
                # Progress
                fill_width = icon_rect.width() * (val / 100.0)
                fill_rect = QRectF(icon_rect.left(), bar_y, fill_width, bar_height)
                
                # Green color
                painter.fillRect(fill_rect, QColor("#2ecc71"))

        # Draw Text
        text_x = icon_rect.right() + 10
        text_width = option.rect.right() - text_x - 10
        
        if text_width > 0:
            # Main label (Folder Name)
            folder_name = index.data(0)
            stats_text = index.data(Qt.ItemDataRole.UserRole + 5)
            
            painter.setFont(self.video_title.font())
            painter.setPen(self.video_title.palette().color(QPalette.ColorRole.WindowText))
            
            fm = painter.fontMetrics()
            line_height = fm.lineSpacing()
            
            # 1. Calculate Name Height (Max 2 lines)
            layout = QTextLayout(str(folder_name), painter.font())
            layout.setCacheEnabled(True)
            layout.beginLayout()
            
            lines = []
            max_lines = 2
            
            while len(lines) < max_lines:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(text_width)
                lines.append(line)
            layout.endLayout()

            name_height = sum(line.height() for line in lines) if lines else line_height
            
            # 2. Calculate Stats Height
            stats_height = 0
            if stats_text:
                stats_height = line_height
            
            # 3. Total text block height
            spacing = 2
            total_text_height = name_height + (spacing + stats_height if stats_text else 0)
            
            # 4. Starting Y to center the block vertically
            start_y = option.rect.center().y() - total_text_height / 2
            current_y = start_y
            
            # 5. Draw Name
            if not lines and folder_name:
                 # Fallback
                 elided = fm.elidedText(folder_name, Qt.TextElideMode.ElideRight, int(text_width))
                 painter.drawText(int(text_x), int(current_y + fm.ascent()), elided)
                 current_y += line_height
            else:
                for i, line in enumerate(lines):
                    line_y = int(current_y + line.ascent())
                    
                    if i == max_lines - 1:
                        if line.textStart() + line.textLength() < len(folder_name):
                            remaining = folder_name[line.textStart():]
                            elided = fm.elidedText(remaining, Qt.TextElideMode.ElideRight, int(text_width))
                            painter.drawText(int(text_x), line_y, elided)
                            current_y += line.height()
                            continue

                    line.draw(painter, QPointF(float(text_x), float(current_y)))
                    current_y += line.height()
            
            # 6. Draw Stats
            if stats_text:
                current_y += spacing
                # Use a slightly smaller font? keeping same for now or self.video_info.font()
                painter.setFont(self.video_info.font())
                painter.setPen(QColor('#CCCCCC'))
                fm_stats = painter.fontMetrics()
                
                elided_stats = fm_stats.elidedText(stats_text, Qt.TextElideMode.ElideRight, int(text_width))
                painter.drawText(int(text_x), int(current_y + fm_stats.ascent()), elided_stats)


        painter.restore()



class HoverTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self._on_hover_timer)
        self.current_hover_index = None
        self.thumbnail_frame = 0
        self.animation_interval = 500
        self.mouse_pos = None

    def set_animation_interval(self, interval):
        self.animation_interval = interval

    def mouseMoveEvent(self, event):
        try:
            self.mouse_pos = event.pos()
            
            index = self.indexAt(event.pos())

            if index.isValid():
                item_type = index.data(Qt.ItemDataRole.UserRole + 1)
                
                if item_type == 'video':
                    delegate = self.itemDelegate()
                    
                    if isinstance(delegate, VideoItemDelegate):
                        visual_rect = self.visualRect(index)
                        
                        if visual_rect.isNull():
                             return

                        play_rect = delegate.get_play_button_rect(visual_rect)
                        
                        if play_rect.contains(event.pos()):
                            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        elif delegate.get_marker_at_pos(visual_rect, event.pos(), index):
                            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        else:
                            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

                        # Update hover state in delegate
                        if index != self.current_hover_index:
                            self.current_hover_index = index
                            self.thumbnail_frame = 0
                            delegate.set_hovered_index(index, 0, mouse_pos=event.pos())
                            self.hover_timer.start(self.animation_interval)
                        else:
                            delegate.set_hovered_index(index, self.thumbnail_frame, mouse_pos=event.pos())
                        
                        self.viewport().update()
                        return
                else:
                    self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                self.stop_hover()
            
            super().mouseMoveEvent(event)

        except Exception as e:
            logging.error(f"ERROR in mouseMoveEvent: {e}", exc_info=True)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            delegate = self.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                # Check hover over play button
                play_rect = delegate.get_play_button_rect(self.visualRect(index))
                
                if play_rect.contains(event.pos()):
                    item = self.itemFromIndex(index)
                    if item:
                        file_path = item.data(0, Qt.ItemDataRole.UserRole)
                        # If already playing video - toggle pause
                        main_window = self.window()
                        delegate = self.itemDelegate()
                        if delegate.playing_path == file_path:
                            if hasattr(main_window, 'video_player'):
                                main_window.video_player.play_pause()
                        else:
                            # Otherwise start new
                            if hasattr(main_window, 'play_video_in_player'):
                                main_window.play_video_in_player(item, resume=True)
                        return # Stop processing to avoid standard row selection

        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Draw placeholder when library is empty"""
        try:
            if self.topLevelItemCount() == 0:
                painter = QPainter(self.viewport())
                draw_library_placeholder(painter, self.viewport().rect(), self.topLevelItemCount())
                painter.end()
            else:
                super().paintEvent(event)
        except Exception as e:
            logging.error(f"Error in HoverTreeWidget.paintEvent: {e}")
            super().paintEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.stop_hover()
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor) # Reset cursor on leave

    def stop_hover(self):
        self.hover_timer.stop()
        self.current_hover_index = None
        self.thumbnail_frame = 0

        delegate = self.itemDelegate()
        if isinstance(delegate, VideoItemDelegate):
            delegate.set_hovered_index(None, 0)

    def _on_hover_timer(self):
        try:
            # logging.debug("_on_hover_timer")
            if not self.current_hover_index:
                self.stop_hover()
                return

            delegate = self.itemDelegate()
            if isinstance(delegate, VideoItemDelegate):
                # Check if mouse is still inside item
                # We trust mouseMoveEvent to call stop_hover if we leave
                # But we should update frame
                self.thumbnail_frame += 1
                # logging.debug(f"timer update frame {self.thumbnail_frame}")
                delegate.set_hovered_index(self.current_hover_index, self.thumbnail_frame, self.mouse_pos)
                self.viewport().update(self.visualRect(self.current_hover_index))
        except Exception as e:
            logging.error(f"ERROR in _on_hover_timer: {e}", exc_info=True)
            self.stop_hover()

