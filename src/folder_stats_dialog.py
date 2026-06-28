from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame, QPushButton, QWidget
from PyQt6.QtCore import Qt, QRectF, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from translator import tr

class DonutChart(QWidget):
    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.stats = stats
        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)
        
        # Default colors
        self._watchedColor = QColor("#2ecc71")
        self._inProgressColor = QColor("#f1c40f")
        self._unwatchedColor = QColor("#ff6b6b")
        self._holeColor = QColor("#373737")
        self._centerTextColor = QColor("#ffffff")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        size = min(rect.width(), rect.height())
        chart_rect = QRectF((rect.width() - size) / 2 + 10, (rect.height() - size) / 2 + 10, size - 20, size - 20)

        total = self.stats['total_videos']
        if total == 0:
            return

        watched = self.stats['watched_videos']
        in_progress = self.stats['in_progress_videos']
        unwatched = self.stats['unwatched_videos']

        start_angle = 90 * 16
        
        self._draw_segment(painter, chart_rect, start_angle, watched, total, self._watchedColor)
        start_angle -= (watched / total) * 360 * 16
        
        self._draw_segment(painter, chart_rect, start_angle, in_progress, total, self._inProgressColor)
        start_angle -= (in_progress / total) * 360 * 16
        
        self._draw_segment(painter, chart_rect, start_angle, unwatched, total, self._unwatchedColor)

        # Draw Center Hole
        painter.setBrush(self._holeColor)
        painter.setPen(Qt.PenStyle.NoPen)
        hole_size = size * 0.6
        hole_rect = QRectF((rect.width() - hole_size) / 2, (rect.height() - hole_size) / 2, hole_size, hole_size)
        painter.drawEllipse(hole_rect)
        
        # Draw Center Text
        painter.setPen(self._centerTextColor)
        font = painter.font()
        font.setPixelSize(int(size * 0.15))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.stats['progress_percent']}%")

    def _draw_segment(self, painter, rect, start_angle, value, total, color):
        if value > 0:
            span_angle = -(value / total) * 360 * 16
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(rect, int(start_angle), int(span_angle))

    # Properties for QSS styling
    @pyqtProperty(QColor)
    def watchedColor(self): return self._watchedColor
    
    @watchedColor.setter
    def watchedColor(self, color): self._watchedColor = color; self.update()

    @pyqtProperty(QColor)
    def inProgressColor(self): return self._inProgressColor
    
    @inProgressColor.setter
    def inProgressColor(self, color): self._inProgressColor = color; self.update()

    @pyqtProperty(QColor)
    def unwatchedColor(self): return self._unwatchedColor
    
    @unwatchedColor.setter
    def unwatchedColor(self, color): self._unwatchedColor = color; self.update()

    @pyqtProperty(QColor)
    def holeColor(self): return self._holeColor
    
    @holeColor.setter
    def holeColor(self, color): self._holeColor = color; self.update()

    @pyqtProperty(QColor)
    def centerTextColor(self): return self._centerTextColor
    
    @centerTextColor.setter
    def centerTextColor(self, color): self._centerTextColor = color; self.update()

class FolderStatsDialog(QDialog):
    def __init__(self, stats: dict, folder_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('stats.title', name=folder_name))
        
        # Set object name for styling
        self.setObjectName("FolderStatsDialog")
        
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        # Styles are now in dark.qss
        self.setup_ui(stats, folder_name)

    def setup_ui(self, stats, folder_name):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel(folder_name)
        title.setObjectName("StatsTitle")
        header_layout.addWidget(title)
        
        subtitle = QLabel(tr('stats.subtitle', total=stats['total_videos']))
        subtitle.setObjectName("StatsSubtitle")
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)

        # Content Area (Chart + Stats)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left Side: Donut Chart
        chart_container = QFrame()
        # chart_container style is handled by #FolderStatsDialog QFrame in QSS
        
        chart_layout = QVBoxLayout(chart_container)
        chart = DonutChart(stats)
        chart_layout.addWidget(chart, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Add legend below chart
        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(5)
        legend_layout.addWidget(self._create_legend_item(tr('stats.watched'), "watched"))
        legend_layout.addWidget(self._create_legend_item(tr('stats.in_progress'), "in_progress"))
        legend_layout.addWidget(self._create_legend_item(tr('stats.unwatched'), "unwatched"))
        chart_layout.addLayout(legend_layout)
        
        content_layout.addWidget(chart_container)

        # Right Side: Detailed Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(15)

        # Progress Bar Card
        progress_container = QFrame()
        p_layout = QVBoxLayout(progress_container)
        p_header = QHBoxLayout()
        p_label = QLabel(tr('stats.progress'))
        p_label.setObjectName("ProgressLabel")
        p_header.addWidget(p_label)
        p_layout.addLayout(p_header)
        
        progress_bar = QProgressBar()
        progress_bar.setValue(int(stats['progress_percent']))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(10)
        progress_bar.setObjectName("FolderStatsProgressBar")
        p_layout.addWidget(progress_bar)
        stats_layout.addWidget(progress_container)
        
        # Grid for Numbers
        grid_container = QFrame()
        grid_layout = QHBoxLayout(grid_container)
        
        # Videos Column
        v_col = QVBoxLayout()
        v_col.addWidget(self.create_stat_row(tr('stats.watched'), stats['watched_videos'], "watched"))
        v_col.addWidget(self.create_stat_row(tr('stats.in_progress'), stats['in_progress_videos'], "in_progress"))
        v_col.addWidget(self.create_stat_row(tr('stats.unwatched'), stats['unwatched_videos'], "unwatched"))
        grid_layout.addLayout(v_col)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setObjectName("StatsSeparator")
        grid_layout.addWidget(line)

        # Time Column
        t_col = QVBoxLayout()
        t_col.addWidget(self.create_stat_row(tr('stats.total_time'), self._format_duration(stats['total_duration'])))
        t_col.addWidget(self.create_stat_row(tr('stats.watched_time'), self._format_duration(stats['watched_duration'])))
        t_col.addWidget(self.create_stat_row(tr('stats.remaining'), self._format_duration(stats['remaining_duration'])))
        grid_layout.addLayout(t_col)

        stats_layout.addWidget(grid_container)
        stats_layout.addStretch()
        
        content_layout.addLayout(stats_layout)
        layout.addLayout(content_layout)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        close_btn = QPushButton(tr('dialog.close'))
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        layout.addLayout(footer_layout)

    def _create_legend_item(self, text, status):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        dot = QLabel("●")
        dot.setObjectName("LegendDot")
        dot.setProperty("status", status)
        
        label = QLabel(text)
        label.setObjectName("LegendLabel")
        
        layout.addWidget(dot)
        layout.addWidget(label)
        return widget

    def create_stat_row(self, label, value, status="default"):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(5, 5, 5, 5)
        
        lbl = QLabel(label)
        lbl.setObjectName("StatsLabel")
        
        val = QLabel(str(value))
        val.setObjectName("StatsValue")
        val.setProperty("status", status)
        
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(val)
        return row

    def _format_duration(self, seconds):
        if seconds <= 0:
            return "0m"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
