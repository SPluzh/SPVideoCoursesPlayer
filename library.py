from pathlib import Path
import logging
import zlib
from collections import OrderedDict

from PyQt6.QtWidgets import QTreeWidget, QStyledItemDelegate, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QRectF, QPointF, QEvent, QModelIndex
from PyQt6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QPainter,
    QPixmap,
    QPalette,
    QBrush,
    QStandardItem,
    QFont,
    QPen,
    QFontMetrics,
    QPainterPath,
    QTextLayout,
    QTextOption,
    QPolygon,
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
        self.THUMBNAIL_CACHE_MAX = 200
        self.thumbnail_cache = OrderedDict()
        self.playing_path = None
        self.is_paused = True
        self.mouse_pos = None
        self.NESTING_COLORS = [
            QColor("#3498db"),  # Blue
            QColor("#9b59b6"),  # Purple
            QColor("#e74c3c"),  # Red
            QColor("#2ecc71"),  # Light green
            QColor("#8e44ad"),  # Deep purple
            QColor("#d35400"),  # Pumpkin
            QColor("#c0392b"),  # Dark red
            QColor("#16a085"),  # Sea green
            QColor("#2980b9"),  # Strong blue
        ]
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

        self.status_watched = QLabel()
        self.status_watched.setObjectName("duration_label_watched")

        self.status_started = QLabel()
        self.status_started.setObjectName("duration_label_started")

        self.status_new = QLabel()
        self.status_new.setObjectName("duration_label_new")

        self.row_play_button_bg = QWidget()
        self.row_play_button_bg.setObjectName("row_play_button_bg")

        self.row_play_button_icon = QLabel()
        self.row_play_button_icon.setObjectName("row_play_button_icon")

        all_widgets = [
            self.thumbnail_border,
            self.progress_bar_bg,
            self.progress_bar_fill,
            self.dot_active,
            self.dot_inactive,
            self.empty_thumbnail_bg,
            self.empty_thumbnail_border,
            self.empty_thumbnail_icon,
            self.duration_label_bg,
            self.duration_label_text,
            self.video_title,
            self.video_info,
            self.row_play_button_bg,
            self.row_play_button_icon,
            self.status_watched,
            self.status_started,
            self.status_new,
        ]
        for widget in all_widgets:
            widget.ensurePolished()

    def set_hovered_index(self, index, thumbnail_index=0, mouse_pos=None):
        self.hovered_index = index
        self.current_thumbnail_index = thumbnail_index
        self.mouse_pos = mouse_pos

    def get_play_button_rect(self, rect, index=None):
        """Return Play button area on thumbnail."""
        try:
            display_width = self.config["display_width"]
            display_height = self.config["display_height"]

            # Sync with paint() logic for nesting_offset
            nesting_offset = 0
            if index is not None and index.isValid():
                chain = self._get_nesting_chain(index)
                if len(chain) > 0:
                    tree = self.parent()
                    indent = 20
                    if hasattr(tree, "indentation"):
                        indent = tree.indentation()
                    nesting_offset = indent

            base_height = self.config["video_row_height"]
            thumb_y = rect.top() + (base_height - display_height) // 2
            thumb_rect = QRect(
                rect.left() + nesting_offset + 5, thumb_y, display_width, display_height
            )

            btn_size = 28  # Slightly smaller for corner
            margin = 2
            return QRect(
                thumb_rect.right() - btn_size - margin,
                thumb_rect.top() + margin,
                btn_size,
                btn_size,
            )
        except Exception as e:
            logging.error(f"Error in get_play_button_rect: {e}")
            return QRect()

    def sizeHint(self, option, index):
        try:
            # import sys; sys.stderr.write(f"[SIZEHINT] row={index.row()}\n"); sys.stderr.flush()
            size = super().sizeHint(option, index)
            item_type = index.data(Qt.ItemDataRole.UserRole + 1)
            if item_type == "folder":
                base_height = self.config["folder_row_height"]

                # Add extra space for horizontal line below expanded folders
                # Progress bar: gap(2) + bar_height(8) + line_gap(2) + line_width(2) = 14px
                extra_height = 14
                size.setHeight(base_height + extra_height)
            elif item_type == "video":
                base_height = self.config["video_row_height"]

                # Check for markers to increase height
                data = index.data(Qt.ItemDataRole.UserRole + 2)
                marker_height = 0
                show_markers = self.config.get("show_markers", True)
                if (
                    show_markers
                    and data
                    and isinstance(data, VideoItemData)
                    and getattr(data, "markers", None)
                ):
                    # 20px per marker line
                    marker_height = len(data.markers) * 20 + 4  # 4px padding

                size.setHeight(base_height + marker_height)

            return size
        except Exception as e:
            logging.error(f"Error in sizeHint: {e}")
            return super().sizeHint(option, index)

    def _get_nesting_chain(self, index):
        """Get the chain of parent paths for consistent color hashing and last-child info."""
        chain = []
        current = index.parent()
        while current.isValid():
            parent_path = current.data(Qt.ItemDataRole.UserRole)

            # Check if this parent was the last child in ITS parent
            is_last = False
            p_idx = current.parent()
            if p_idx.isValid():
                is_last = current.row() == p_idx.model().rowCount(p_idx) - 1
            else:
                model = current.model()
                if model:
                    is_last = current.row() == model.rowCount(QModelIndex()) - 1

            if parent_path:
                chain.insert(0, (str(parent_path), is_last))  # Top parents first
            else:
                chain.insert(0, (f"unknown_{len(chain)}", is_last))
            current = p_idx
        return chain

    def _draw_nesting_lines(self, painter, rect, chain, index=None):
        """Draw colored vertical lines indicating nesting depth, colored uniquely by parent paths."""
        # Check if tree lines should be shown
        if not self.config.get("show_tree_lines", True):
            return 0

        depth = len(chain)
        if depth <= 0:
            return 0

        line_width = 2

        # Get tree indentation to align lines perfectly between parent and child items
        tree = self.parent()
        indent = 20
        if hasattr(tree, "indentation"):
            indent = tree.indentation()

        spacing = max(2, indent - line_width)

        # Determine if this item is the last child of its immediate parent
        is_last_child = False
        if index is not None and index.isValid() and index.parent().isValid():
            p_idx = index.parent()
            is_last_child = index.row() == p_idx.model().rowCount(p_idx) - 1

        # Check item type (video or folder)
        is_video = False
        is_folder = False
        if index is not None and index.isValid():
            item_type = index.data(Qt.ItemDataRole.UserRole + 1)
            is_video = item_type == "video"
            is_folder = item_type == "folder"

        # Calculate the center Y position of the thumbnail/icon (not the entire row)
        # because markers below videos increase row height
        branch_y = rect.top() + rect.height() / 2  # Default: middle of row
        if is_video:
            base_height = self.config["video_row_height"]
            # Thumbnail is vertically centered within base_height
            thumb_center_y = rect.top() + base_height / 2
            branch_y = thumb_center_y
        elif is_folder:
            # For folders, use middle of the row (not icon center)
            branch_y = rect.top() + rect.height() / 2

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        for i in range(depth):
            parent_path_str, _ = chain[i]

            # If an ancestor line already ended in a previous folder, skip drawing it for descendants
            if i < depth - 1:
                child_is_last = chain[i + 1][1]
                if child_is_last:
                    continue

            # Hash the path to get a stable positive integer
            path_hash = zlib.adler32(parent_path_str.encode("utf-8", errors="ignore"))
            color_index = path_hash % len(self.NESTING_COLORS)
            color = self.NESTING_COLORS[color_index]

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            # The core trick: shift lines leftwards by `indent` depending on their level
            # so they perfectly align with the parent's line.
            line_x = rect.left() - (depth - 1 - i) * indent

            # Special handling for video items: draw branch connector
            if is_video and i == depth - 1:
                # This is the immediate parent's line for a video item
                if is_last_child:
                    # Last child: L-shape (└) - vertical line from top to branch point only
                    painter.drawRect(
                        QRectF(
                            line_x,
                            rect.top(),
                            line_width,
                            branch_y - rect.top() + line_width / 2,
                        )
                    )
                else:
                    # Middle child: T-shape (├) - full vertical line through entire height
                    painter.drawRect(
                        QRectF(line_x, rect.top(), line_width, rect.height())
                    )

                # Horizontal branch line (pointing to thumbnail) - aligned with thumbnail center
                painter.drawRect(
                    QRectF(
                        line_x,
                        branch_y - line_width / 2,
                        indent,
                        line_width,
                    )
                )
            elif is_folder and i == depth - 1:
                # Folder item: draw branch connector
                if is_last_child:
                    # Last child: L-shape (└) - vertical line from top to branch point only
                    painter.drawRect(
                        QRectF(
                            line_x,
                            rect.top(),
                            line_width,
                            branch_y - rect.top() + line_width / 2,
                        )
                    )
                else:
                    # Middle child: T-shape (├) - full vertical line through entire height
                    painter.drawRect(
                        QRectF(line_x, rect.top(), line_width, rect.height())
                    )

                # Horizontal branch line (pointing to folder icon) - aligned with icon center
                painter.drawRect(
                    QRectF(
                        line_x,
                        branch_y - line_width / 2,
                        indent,
                        line_width,
                    )
                )
            else:
                # Normal full vertical line for:
                # - Ancestor lines (i < depth - 1)
                if not ((is_video or is_folder) and i == depth - 1):
                    # Normal case: draw full vertical line
                    painter.drawRect(
                        QRectF(line_x, rect.top(), line_width, rect.height())
                    )

        painter.restore()

        # We only need to shift the thumbnail by the width of the last line plus spacing,
        # because the other lines were drawn to the left, inside the branch area.
        return line_width + spacing

    def _get_pixmap(self, path):
        # We cache pixmaps at physical resolution (logical * dpr) to keep them sharp.
        dpr = 1.0
        try:
            parent = self.parent()
            if parent and parent.window() and parent.window().windowHandle():
                dpr = parent.window().windowHandle().devicePixelRatio()
        except:
            pass

        cache_key = (path, dpr)
        if cache_key in self.thumbnail_cache:
            self.thumbnail_cache.move_to_end(cache_key)
            return self.thumbnail_cache[cache_key]

        pixmap = None
        if path and Path(path).exists():
            raw = QPixmap(path)
            if not raw.isNull():
                # Scale to physical resolution
                dw = int(self.config.get("display_width", 192) * dpr)
                dh = int(self.config.get("display_height", 108) * dpr)

                pixmap = raw.scaled(
                    dw,
                    dh,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if pixmap:
                    pixmap.setDevicePixelRatio(dpr)

        if len(self.thumbnail_cache) >= self.THUMBNAIL_CACHE_MAX:
            self.thumbnail_cache.popitem(last=False)
        self.thumbnail_cache[cache_key] = pixmap
        return pixmap

    def paint(self, painter, option, index):  # Overridden
        try:
            if not index.isValid():
                return

            # Erase the entire row rect with the window background before drawing anything.
            # Qt does NOT clear the backing store between partial repaints, so without this
            # pixels from the previous frame "ghost" through on every thumbnail change.
            painter.fillRect(option.rect, option.palette.color(QPalette.ColorRole.Base))

            item_type = index.data(Qt.ItemDataRole.UserRole + 1)

            # Handle Folder Rendering
            if item_type == "folder":
                self.paint_folder(painter, option, index)
                return

            if item_type != "video":
                super().paint(painter, option, index)
                return

            painter.save()
            data = index.data(Qt.ItemDataRole.UserRole + 2)
            if not data:
                painter.restore()
                return

            # Draw nesting lines
            chain = self._get_nesting_chain(index)
            nesting_offset = self._draw_nesting_lines(
                painter, option.rect, chain, index
            )

            # Unpack data
            if isinstance(data, VideoItemData):
                filename = data.filename
                duration = data.duration
                resolution = data.resolution
                file_size = data.file_size
                watched_percent = data.watched_percent
                thumbnail_path = data.thumbnail_path
                thumbnails_list = getattr(data, "thumbnails_list", []) or []
                last_position = data.last_position
                marker_count = data.marker_count
                is_favorite = data.is_favorite
                tags = getattr(data, "tags", []) or []
                markers = getattr(data, "markers", []) or []
            else:
                # Fallback for old data or tuple/list
                markers = []
                tags = []
                thumbnails_list = []
                if isinstance(data, (tuple, list)) and len(data) >= 9:
                    (
                        filename,
                        duration,
                        resolution,
                        file_size,
                        watched_percent,
                        thumbnail_path,
                        thumbnails_list,
                        last_position,
                        marker_count,
                    ) = data[:9]
                    is_favorite = 0
                else:
                    painter.restore()
                    return

            display_width = self.config["display_width"]
            display_height = self.config["display_height"]

            # If we are effectively "under" the main row content, we should standardise top alignment for main content
            # But sizeHint logic: size.setHeight(base_height + marker_height)
            # So the "main" part (thumb + text) is in the first `base_height` pixels.
            # We should recalculate thumb_y to be centered in that base_height, or fixed top offset.
            # Current logic centers it in the FULL rect height which includes markers. This is WRONG if markers are huge.

            base_height = self.config["video_row_height"]
            thumb_y = option.rect.top() + (base_height - display_height) // 2

            thumb_rect = QRect(
                option.rect.left() + nesting_offset + 5,
                thumb_y,
                display_width,
                display_height,
            )

            current_thumb = thumbnail_path
            if (
                self.hovered_index is not None
                and self.hovered_index == index
                and thumbnails_list
            ):
                thumb_index = self.current_thumbnail_index % len(thumbnails_list)
                current_thumb = thumbnails_list[thumb_index]

            pixmap = self._get_pixmap(current_thumb)
            if pixmap:
                # Pixmap is already pre-scaled in _get_pixmap LRU cache
                x_offset = (display_width - pixmap.width()) // 2
                y_offset = (display_height - pixmap.height()) // 2

                path = QPainterPath()
                path.addRoundedRect(QRectF(thumb_rect), 3.0, 3.0)
                painter.save()
                painter.setClipPath(path)
                painter.fillRect(
                    thumb_rect,
                    self.empty_thumbnail_bg.palette().color(QPalette.ColorRole.Window),
                )

                # Logic to center the pixmap inside thumb_rect if its aspect ratio differs
                # px_w/px_h here are logical because pixmap has devicePixelRatio set
                px_w = pixmap.width() / pixmap.devicePixelRatio()
                px_h = pixmap.height() / pixmap.devicePixelRatio()

                target_x = thumb_rect.left() + (display_width - px_w) / 2
                target_y = thumb_rect.top() + (display_height - px_h) / 2
                target_rect = QRectF(target_x, target_y, px_w, px_h)

                painter.drawPixmap(target_rect, pixmap, QRectF(pixmap.rect()))
                painter.restore()

                playing_file = index.data(Qt.ItemDataRole.UserRole)
                if self.playing_path and playing_file == self.playing_path:
                    pen = QPen(QColor(1, 133, 116), 8)
                    painter.setPen(pen)
                    painter.drawRoundedRect(thumb_rect.adjusted(-4, -4, 4, 4), 7, 7)
                else:
                    painter.setPen(
                        self.thumbnail_border.palette().color(QPalette.ColorRole.Mid)
                    )
                    painter.drawRoundedRect(thumb_rect, 3, 3)

                if last_position > 0 and duration > 0:
                    progress_percent = (last_position / duration) * 100
                    progress_bar_height = self.progress_bar_bg.minimumHeight() or 5
                    progress_bar_y = thumb_rect.bottom() - progress_bar_height - 1
                    progress_bar_rect = QRect(
                        thumb_rect.left() + 1,
                        progress_bar_y,
                        display_width - 2,
                        progress_bar_height,
                    )
                    painter.fillRect(
                        progress_bar_rect,
                        self.progress_bar_bg.palette().color(QPalette.ColorRole.Window),
                    )
                    filled_width = int((display_width - 2) * progress_percent / 100)
                    if filled_width > 0:
                        filled_rect = QRect(
                            progress_bar_rect.left(),
                            progress_bar_rect.top(),
                            filled_width,
                            progress_bar_height,
                        )
                        painter.fillRect(
                            filled_rect,
                            self.progress_bar_fill.palette().color(
                                QPalette.ColorRole.Window
                            ),
                        )

                if (
                    self.hovered_index is not None
                    and self.hovered_index == index
                    and thumbnails_list
                ):
                    painter.save()
                    # Enable antialiasing for smooth round dots
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

                    # Use float coordinates for stable positioning on High DPI screens
                    dot_y = float(thumb_rect.top()) + 8.0
                    dot_width = 6.0
                    dot_spacing = 2.0
                    total_dots_width = (
                        dot_width * len(thumbnails_list)
                        + (len(thumbnails_list) - 1) * dot_spacing
                    )
                    start_x = (
                        float(thumb_rect.left())
                        + (float(display_width) - total_dots_width) / 2.0
                    )

                    for i in range(len(thumbnails_list)):
                        dot_x = start_x + i * (dot_width + dot_spacing)
                        if i == self.current_thumbnail_index % len(thumbnails_list):
                            painter.setBrush(
                                self.dot_active.palette().color(
                                    QPalette.ColorRole.Window
                                )
                            )
                        else:
                            painter.setBrush(
                                self.dot_inactive.palette().color(
                                    QPalette.ColorRole.Window
                                )
                            )
                        painter.setPen(Qt.PenStyle.NoPen)
                        # Draw using QRectF for sub-pixel precision and to avoid jumping
                        painter.drawEllipse(QRectF(dot_x, dot_y, dot_width, dot_width))
                    painter.restore()
            else:
                painter.fillRect(
                    thumb_rect,
                    self.empty_thumbnail_bg.palette().color(QPalette.ColorRole.Window),
                )
                painter.setPen(
                    self.empty_thumbnail_border.palette().color(QPalette.ColorRole.Mid)
                )
                painter.drawRoundedRect(thumb_rect, 3, 3)
                painter.setPen(
                    self.empty_thumbnail_icon.palette().color(
                        QPalette.ColorRole.WindowText
                    )
                )
                painter.setFont(self.empty_thumbnail_icon.font())
                painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "\U0001f3ac")

            if is_favorite:
                painter.save()
                heart_size = 24
                heart_rect = QRect(
                    thumb_rect.left() - 6, thumb_rect.top() - 6, heart_size, heart_size
                )
                font = painter.font()
                font.setPointSize(20)
                painter.setFont(font)
                painter.setPen(QColor(0, 0, 0, 200))
                painter.drawText(
                    heart_rect.adjusted(1, 1, 1, 1),
                    Qt.AlignmentFlag.AlignCenter,
                    "\u2665",
                )
                painter.setPen(QColor("#e74c3c"))
                painter.drawText(heart_rect, Qt.AlignmentFlag.AlignCenter, "\u2665")
                painter.restore()

            if duration:
                duration_str = self.config["format_duration"](duration)
                painter.setFont(self.duration_label_text.font())
                text_rect = painter.fontMetrics().boundingRect(duration_str)
                bg_rect = QRect(
                    thumb_rect.right() - text_rect.width() - 8,
                    thumb_rect.bottom() - text_rect.height() - 10,
                    text_rect.width() + 6,
                    text_rect.height() + 4,
                )

                # Determine background color based on progress
                if watched_percent == 100:
                    bg_color = self.status_watched.palette().color(
                        QPalette.ColorRole.Window
                    )
                elif watched_percent > 0 or last_position > 0:
                    bg_color = self.status_started.palette().color(
                        QPalette.ColorRole.Window
                    )
                else:
                    bg_color = self.status_new.palette().color(
                        QPalette.ColorRole.Window
                    )

                # Apply opacity if it's a solid color from statusOk/statusWarning
                if bg_color.alpha() == 255:
                    bg_color.setAlpha(180)

                painter.setBrush(bg_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 2, 2)
                painter.setPen(
                    self.duration_label_text.palette().color(
                        QPalette.ColorRole.WindowText
                    )
                )
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, duration_str)

            text_x = thumb_rect.right() + 12
            text_y = option.rect.top() + 8

            # NOTE: available_width must be calculated carefully to avoid negative values
            available_width = max(1, option.rect.right() - text_x - 10)

            painter.setFont(self.video_title.font())
            painter.setPen(
                self.video_title.palette().color(QPalette.ColorRole.WindowText)
            )

            fm = painter.fontMetrics()
            layout = QTextLayout(str(filename), painter.font())
            layout.setCacheEnabled(True)
            layout.beginLayout()

            lines = []
            max_lines = 4
            while len(lines) < max_lines:
                line = layout.createLine()
                if not line.isValid() or line.textLength() == 0:
                    break
                line.setLineWidth(available_width)
                lines.append(line)
            layout.endLayout()

            title_height = 0
            if not lines and filename:
                elided = fm.elidedText(
                    str(filename), Qt.TextElideMode.ElideRight, available_width
                )
                painter.drawText(int(text_x), int(text_y + fm.ascent()), elided)
                title_height = fm.lineSpacing()
            else:
                for i, line in enumerate(lines):
                    line_y = int(text_y + title_height + line.ascent())

                    if (
                        i == max_lines - 1
                        and line.textStart() + line.textLength() < len(str(filename))
                    ):
                        remaining = str(filename)[line.textStart() :]
                        elided = fm.elidedText(
                            remaining, Qt.TextElideMode.ElideRight, available_width
                        )
                        painter.drawText(int(text_x), line_y, elided)
                    else:
                        line.draw(
                            painter,
                            QPointF(float(text_x), float(text_y + title_height)),
                        )

                    title_height += line.height()

            text_y += max(25, int(title_height) + 4)

            if tags:
                tag_x = text_x
                tag_y = text_y + 2
                tag_height = 18
                painter.save()
                font = painter.font()
                font.setPointSize(8)
                font.setBold(True)
                painter.setFont(font)
                for tag in tags:
                    name = str(tag.get("name", ""))
                    color = QColor(tag.get("color") or "#3498db")
                    tag_width = painter.fontMetrics().horizontalAdvance(name) + 12
                    if tag_x + tag_width > option.rect.right():
                        break
                    tag_rect = QRect(tag_x, tag_y, tag_width, tag_height)
                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(tag_rect, 6, 6)
                    r, g, b, _ = color.getRgb()
                    luminance = 0.299 * r + 0.587 * g + 0.114 * b
                    text_color = (
                        QColor("#000000") if luminance > 128 else QColor("#ffffff")
                    )
                    painter.setPen(text_color)
                    painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, name)
                    tag_x += tag_width + 6
                painter.restore()
                # text_y += 20 # removed increment since markers are now separate

            is_playing_item = (
                self.playing_path
                and index.data(Qt.ItemDataRole.UserRole) == self.playing_path
            )
            if self.hovered_index == index or is_playing_item:
                play_btn_rect = self.get_play_button_rect(option.rect, index)

                is_over_btn = False
                if self.mouse_pos and play_btn_rect.contains(self.mouse_pos):
                    is_over_btn = True

                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                painter.setBrush(
                    self.row_play_button_bg.palette().color(QPalette.ColorRole.Window)
                )

                if not is_over_btn and self.hovered_index != index:
                    color = self.row_play_button_bg.palette().color(
                        QPalette.ColorRole.Window
                    )
                    color.setAlpha(150)
                    painter.setBrush(color)
                elif is_over_btn:
                    color = self.row_play_button_bg.palette().color(
                        QPalette.ColorRole.Window
                    )
                    painter.setBrush(color.lighter(110))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(play_btn_rect, 3, 3)

                icon_color = self.row_play_button_icon.palette().color(
                    QPalette.ColorRole.WindowText
                )
                painter.setBrush(icon_color)
                painter.setPen(Qt.PenStyle.NoPen)

                if is_playing_item and not self.is_paused:
                    bar_w = 4
                    bar_h = 14
                    gap = 4
                    center = play_btn_rect.center() + QPoint(1, 1)
                    rect1 = QRect(
                        center.x() - bar_w - gap // 2,
                        center.y() - bar_h // 2,
                        bar_w,
                        bar_h,
                    )
                    rect2 = QRect(
                        center.x() + gap // 2, center.y() - bar_h // 2, bar_w, bar_h
                    )
                    painter.drawRect(rect1)
                    painter.drawRect(rect2)
                else:
                    tri_w = 12
                    tri_h = 14
                    center = play_btn_rect.center() + QPoint(1, 1)
                    triangle = QPolygon(
                        [
                            QPoint(center.x() - tri_w // 2, center.y() - tri_h // 2),
                            QPoint(center.x() + tri_w // 2, center.y()),
                            QPoint(center.x() - tri_w // 2, center.y() + tri_h // 2),
                        ]
                    )
                    painter.drawPolygon(triangle)

            # Markers under thumbnail
            show_markers = self.config.get("show_markers", True)
            if show_markers and markers:
                # Align with thumbnail left
                marker_x = thumb_rect.left()
                # Start below the base height (thumb + text block)
                marker_y = option.rect.top() + self.config["video_row_height"]
                marker_height = 18

                painter.save()
                base_font = painter.font()
                base_font.setPointSize(9)
                painter.setFont(base_font)

                # Check for hovered marker
                hovered_marker = (
                    self.get_marker_at_pos(option.rect, self.mouse_pos, index)
                    if self.hovered_index == index and self.mouse_pos
                    else None
                )

                # Full width for markers? or limited?
                # "под картинкой" -> under picture. Let's start at thumb left,
                # but allow width to extend to right edge (minus margin)
                marker_area_width = max(1, option.rect.right() - marker_x - 10)

                for marker in markers:
                    if marker_y > option.rect.bottom():
                        break
                    try:
                        time_str = self.config["format_duration"](
                            marker["position_seconds"]
                        )
                    except:
                        time_str = "00:00"
                    label = str(marker.get("label", ""))
                    display_text = f"[{time_str}] {label}"
                    stripe_color = QColor(marker.get("color", "#3498db") or "#3498db")

                    painter.fillRect(
                        QRect(marker_x, marker_y + 2, 4, marker_height - 4),
                        stripe_color,
                    )

                    # Apply bold if hovered
                    if marker == hovered_marker:
                        base_font.setBold(True)
                    else:
                        base_font.setBold(False)
                    painter.setFont(base_font)

                    painter.setPen(QColor("#dddddd"))

                    text_w = max(1, marker_area_width - 16)
                    elided = painter.fontMetrics().elidedText(
                        display_text, Qt.TextElideMode.ElideRight, text_w
                    )
                    painter.drawText(
                        QRect(marker_x + 16, marker_y, text_w, marker_height),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        elided,
                    )
                    marker_y += 20
                painter.restore()

            painter.restore()
        except Exception as e:
            logging.error(f"Error in paint: {e}", exc_info=True)

    def get_marker_at_pos(self, rect, pos, index):
        """Check if position is over a marker."""
        data = index.data(Qt.ItemDataRole.UserRole + 2)
        markers = []
        if isinstance(data, VideoItemData):
            markers = getattr(data, "markers", []) or []

        show_markers = self.config.get("show_markers", True)
        if show_markers and markers:
            base_height = self.config["video_row_height"]

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
                    pos = marker["position_seconds"]
                    tree = self.parent()
                    if tree:
                        window = tree.window()
                        if hasattr(window, "play_video_at_marker"):
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

        # Draw nesting lines
        chain = self._get_nesting_chain(index)
        nesting_offset = self._draw_nesting_lines(painter, option.rect, chain, index)

        # Config dimensions
        video_height = self.config.get("video_row_height", 110)

        # Icon Area
        config = self.config
        # Reserve space for progress bar (8px + 2px padding + bottom padding)
        # So we subtract more from row height
        icon_height = config.get("folder_row_height", 70) - 14
        icon_width = int(icon_height * 16 / 9)

        # Center vertically but shift up slightly to make room below?
        # Or just use row height logic.
        # If we reduce height by 14, we have 7px top/bottom padding if centered.
        # We need 2 (gap) + 8 (bar) = 10px below.
        # So shift up by 3px.

        center_y = option.rect.center().y()
        icon_rect = QRectF(
            option.rect.left() + nesting_offset + 5,
            center_y - icon_height / 2 - 2,  # Shift up 2px
            icon_width,
            icon_height,
        )

        # Draw Icon Background (for missing images or transparent ones)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cover_path = index.data(Qt.ItemDataRole.UserRole + 4)  # Folder image path
        pixmap = self._get_pixmap(cover_path)

        if pixmap:
            # Check if it's the default folder icon
            is_default = "folder_cover.png" in str(cover_path)
            mode = (
                Qt.AspectRatioMode.KeepAspectRatio
                if is_default
                else Qt.AspectRatioMode.KeepAspectRatioByExpanding
            )

            dpr = painter.device().devicePixelRatioF()
            # Scale to physical resolution
            scaled_pixmap = pixmap.scaled(
                int(icon_width * dpr),
                int(icon_height * dpr),
                mode,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled_pixmap.setDevicePixelRatio(dpr)

            # Logic to center the pixmap inside icon_rect if its aspect ratio differs
            px_w = scaled_pixmap.width() / scaled_pixmap.devicePixelRatio()
            px_h = scaled_pixmap.height() / scaled_pixmap.devicePixelRatio()

            px_x = icon_rect.x() + (icon_rect.width() - px_w) / 2
            px_y = icon_rect.y() + (icon_rect.height() - px_h) / 2
            target_rect = QRectF(px_x, px_y, px_w, px_h)

            painter.save()
            clip_path = QPainterPath()
            clip_path.addRoundedRect(icon_rect, 3.0, 3.0)
            painter.setClipPath(clip_path)

            painter.drawPixmap(target_rect, scaled_pixmap, QRectF(scaled_pixmap.rect()))

            # Draw border
            painter.restore()
            painter.setClipping(False)
            painter.setPen(
                self.thumbnail_border.palette().color(QPalette.ColorRole.Mid)
            )
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
                        stripe_width = 4
                        stripe_rect = QRectF(
                            icon_rect.left() - stripe_width,
                            icon_rect.top(),
                            stripe_width,
                            icon_rect.height(),
                        )
                        # Use QPainterPath for partial rounding (only left side)
                        path = QPainterPath()
                        radius = 3
                        # Start from top-right
                        path.moveTo(stripe_rect.right(), stripe_rect.top())
                        # Top edge to start of top-left arc
                        path.lineTo(stripe_rect.left() + radius, stripe_rect.top())
                        # Top-left arc (x, y, w, h, startAngle, spanAngle)
                        path.arcTo(
                            stripe_rect.left(),
                            stripe_rect.top(),
                            2 * radius,
                            2 * radius,
                            90,
                            90,
                        )
                        # Left edge to start of bottom-left arc
                        path.lineTo(stripe_rect.left(), stripe_rect.bottom() - radius)
                        # Bottom-left arc
                        path.arcTo(
                            stripe_rect.left(),
                            stripe_rect.bottom() - 2 * radius,
                            2 * radius,
                            2 * radius,
                            180,
                            90,
                        )
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
            painter.fillRect(
                icon_rect,
                self.empty_thumbnail_bg.palette().color(QPalette.ColorRole.Window),
            )
            painter.setPen(
                self.empty_thumbnail_border.palette().color(QPalette.ColorRole.Mid)
            )
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
            painter.fillRect(bg_rect, QColor(40, 40, 40))  # Dark track

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
            painter.setPen(
                self.video_title.palette().color(QPalette.ColorRole.WindowText)
            )

            fm = painter.fontMetrics()
            line_height = fm.lineSpacing()

            # 1. Calculate Name Height (Max 2 lines)
            layout = QTextLayout(str(folder_name), painter.font())
            layout.setCacheEnabled(True)
            layout.beginLayout()

            lines = []
            max_lines = 3

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
            total_text_height = name_height + (
                spacing + stats_height if stats_text else 0
            )

            # 4. Starting Y to center the block vertically
            start_y = option.rect.center().y() - total_text_height / 2
            current_y = start_y

            # 5. Draw Name
            if not lines and folder_name:
                # Fallback
                elided = fm.elidedText(
                    folder_name, Qt.TextElideMode.ElideRight, int(text_width)
                )
                painter.drawText(int(text_x), int(current_y + fm.ascent()), elided)
                current_y += line_height
            else:
                for i, line in enumerate(lines):
                    line_y = int(current_y + line.ascent())

                    if i == max_lines - 1:
                        if line.textStart() + line.textLength() < len(folder_name):
                            remaining = folder_name[line.textStart() :]
                            elided = fm.elidedText(
                                remaining, Qt.TextElideMode.ElideRight, int(text_width)
                            )
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
                painter.setPen(QColor("#CCCCCC"))
                fm_stats = painter.fontMetrics()

                elided_stats = fm_stats.elidedText(
                    stats_text, Qt.TextElideMode.ElideRight, int(text_width)
                )
                painter.drawText(
                    int(text_x), int(current_y + fm_stats.ascent()), elided_stats
                )

        # Draw horizontal line below expanded folders with children
        tree_widget = option.widget
        if isinstance(tree_widget, QTreeWidget):
            item = tree_widget.itemFromIndex(index)
            if (
                item
                and item.isExpanded()
                and item.childCount() > 0
                and self.config.get("show_tree_lines", True)
            ):
                # Calculate line color using same algorithm as nesting lines
                folder_path = index.data(Qt.ItemDataRole.UserRole)
                path_hash = zlib.adler32(
                    str(folder_path).encode("utf-8", errors="ignore")
                )
                color_index = path_hash % len(self.NESTING_COLORS)
                line_color = self.NESTING_COLORS[color_index]

                # Draw line with same width as nesting lines
                line_width = 2
                pen = QPen(line_color, line_width)
                painter.setPen(pen)

                # Draw line at the very bottom of the row to connect with nesting lines
                y_pos = option.rect.bottom() - 1

                # Determine line start position:
                # If there are vertical nesting lines, start from the leftmost one + 4px
                # Otherwise, start from the left edge of the folder icon
                depth = len(chain)
                if depth > 0:
                    # Get tree indentation
                    tree = self.parent()
                    indent = 20
                    if hasattr(tree, "indentation"):
                        indent = tree.indentation()

                    # Calculate position of leftmost vertical line + 4px offset
                    # The leftmost line is at i=0 in the chain
                    line_start_x = option.rect.left() - (depth - 1) * indent + 4
                else:
                    # No nesting, start from icon left edge
                    line_start_x = option.rect.left() + nesting_offset + 5

                painter.drawLine(line_start_x, y_pos, option.rect.right(), y_pos)

        painter.restore()


class HoverTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setIndentation(10)  # Halved indentation for compact display
        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self._on_hover_timer)
        self.current_hover_index = None
        self.thumbnail_frame = 0
        self.animation_interval = 500
        self.mouse_pos = None

    def set_animation_interval(self, interval):
        self.animation_interval = interval

    def _update_item_rect(self, index):
        """Update viewport for an item, expanding rect to cover the thumbnail
        which is drawn 15px to the left of the visual rect."""
        rect = self.visualRect(index)
        rect.adjust(-20, 0, 0, 0)  # expand left to cover thumbnail offset
        self.viewport().update(rect)

    def mouseMoveEvent(self, event):
        try:
            self.mouse_pos = event.pos()

            index = self.indexAt(event.pos())

            if index.isValid():
                item_type = index.data(Qt.ItemDataRole.UserRole + 1)

                if item_type == "video":
                    delegate = self.itemDelegate()

                    if isinstance(delegate, VideoItemDelegate):
                        visual_rect = self.visualRect(index)

                        if visual_rect.isNull():
                            return

                        play_rect = delegate.get_play_button_rect(visual_rect, index)

                        if play_rect.contains(event.pos()):
                            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        elif delegate.get_marker_at_pos(
                            visual_rect, event.pos(), index
                        ):
                            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
                        else:
                            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

                        # Update hover state in delegate
                        if index != self.current_hover_index:
                            prev_index = self.current_hover_index
                            self.current_hover_index = index
                            self.thumbnail_frame = 0
                            delegate.set_hovered_index(index, 0, mouse_pos=event.pos())
                            self.hover_timer.start(self.animation_interval)
                            # Invalidate previous row so its old thumbnail is cleared
                            if prev_index is not None and prev_index.isValid():
                                self._update_item_rect(prev_index)
                        else:
                            delegate.set_hovered_index(
                                index, self.thumbnail_frame, mouse_pos=event.pos()
                            )

                        self._update_item_rect(index)
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
                play_rect = delegate.get_play_button_rect(self.visualRect(index), index)

                if play_rect.contains(event.pos()):
                    item = self.itemFromIndex(index)
                    if item:
                        file_path = item.data(0, Qt.ItemDataRole.UserRole)
                        # If already playing video - toggle pause
                        main_window = self.window()
                        delegate = self.itemDelegate()
                        if delegate.playing_path == file_path:
                            if hasattr(main_window, "video_player"):
                                main_window.video_player.play_pause()
                        else:
                            # Otherwise start new
                            if hasattr(main_window, "play_video_in_player"):
                                main_window.play_video_in_player(item, resume=True)
                        return  # Stop processing to avoid standard row selection

        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Draw placeholder when library is empty"""
        try:
            if self.topLevelItemCount() == 0:
                painter = QPainter(self.viewport())
                draw_library_placeholder(
                    painter, self.viewport().rect(), self.topLevelItemCount()
                )
                painter.end()
            else:
                super().paintEvent(event)
        except Exception as e:
            logging.error(f"Error in HoverTreeWidget.paintEvent: {e}")
            super().paintEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.stop_hover()
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)  # Reset cursor on leave

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
                delegate.set_hovered_index(
                    self.current_hover_index, self.thumbnail_frame, self.mouse_pos
                )
                self._update_item_rect(self.current_hover_index)
        except Exception as e:
            logging.error(f"ERROR in _on_hover_timer: {e}", exc_info=True)
            self.stop_hover()

    def wheelEvent(self, event):
        """Override wheel event to scroll by single row instead of default 3 rows."""
        try:
            # Get wheel delta (positive = scroll up, negative = scroll down)
            delta = event.angleDelta().y()

            # Determine scroll direction (1 notch = 120 units typically)
            if delta == 0:
                super().wheelEvent(event)
                return

            # Get the index at current scroll position
            index = self.indexAt(self.viewport().rect().topLeft())
            if not index.isValid():
                super().wheelEvent(event)
                return

            # Scroll by exactly 1 item
            if delta > 0:
                # Scroll up - move to previous item
                new_index = self.indexAbove(index)
                if new_index.isValid():
                    self.scrollTo(new_index, QTreeWidget.ScrollHint.PositionAtTop)
            else:
                # Scroll down - move to next item
                new_index = self.indexBelow(index)
                if new_index.isValid():
                    self.scrollTo(new_index, QTreeWidget.ScrollHint.PositionAtTop)

            event.accept()
        except Exception as e:
            logging.error(f"ERROR in wheelEvent: {e}", exc_info=True)
            super().wheelEvent(event)
