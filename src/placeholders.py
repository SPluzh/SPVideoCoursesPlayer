from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QFont, QPen, QBrush, QPolygonF
from PyQt6.QtCore import QPointF, Qt, QRectF
from translator import tr

def draw_video_placeholder(painter, rect):
    """Draw a beautiful placeholder when no video is loaded"""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # 1. Background Gradient
    center = rect.center()
    gradient = QRadialGradient(QPointF(center), max(rect.width(), rect.height()) / 2)
    gradient.setColorAt(0, QColor(30, 30, 30))
    gradient.setColorAt(1, QColor(0, 0, 0))
    painter.fillRect(rect, gradient)
    
    # 2. Draw stylized Play Icon in the center
    accent_color = QColor("#018574")
    icon_size = min(rect.width(), rect.height()) // 5
    if icon_size > 20:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(accent_color.darker(150))) # Glow/Shadow
        
        # Double triangle effect or just a nice triangle
        triangle = QPolygonF([
            QPointF(center.x() - icon_size * 0.4, center.y() - icon_size * 0.5),
            QPointF(center.x() - icon_size * 0.4, center.y() + icon_size * 0.5),
            QPointF(center.x() + icon_size * 0.6, center.y())
        ])
        
        painter.setOpacity(0.3)
        painter.drawPolygon(triangle.translated(2, 2)) # Subtle shadow
        
        painter.setOpacity(0.8)
        painter.setBrush(QBrush(accent_color))
        painter.drawPolygon(triangle)
        
    # 3. Text Message
    painter.setOpacity(1.0) # Unified opacity for title
    painter.setPen(QPen(QColor(200, 200, 200)))
    font = QFont("Inter", 13, QFont.Weight.Bold)
    if not font.exactMatch():
        font = QFont("Segoe UI", 13, QFont.Weight.Bold)
    painter.setFont(font)
    
    text = tr('status.select_video')
    if text == 'status.select_video': # Fallback if key missing
        text = "Select a video to start"
        
    text_rect = painter.fontMetrics().boundingRect(text)
    painter.drawText(
        int(center.x() - text_rect.width() / 2),
        int(center.y() + icon_size * 0.8 + text_rect.height()),
        text
    )

def draw_library_placeholder(painter, rect, item_count):
    """Draw placeholder when library is empty"""
    if item_count != 0:
        return

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    center = rect.center()
    
    # 1. Stylized Folder Icon (Original Style)
    icon_size = 64
    painter.setOpacity(1.0)  # Fully opaque
    painter.setBrush(QBrush(QColor("#018574")))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Move icon up prevents overlap
    icon_y_center = center.y() - 40
    
    # Draw folder shape
    folder_rect = QRectF(float(center.x() - icon_size/2), float(icon_y_center - icon_size / 2), float(icon_size), float(icon_size * 0.7))
    painter.drawRoundedRect(folder_rect, 5, 5)
    # Folder tab
    tab_rect = QRectF(float(center.x() - icon_size/2), float(icon_y_center - icon_size / 2 - icon_size * 0.1), float(icon_size * 0.4), float(icon_size * 0.2))
    painter.drawRoundedRect(tab_rect, 3, 3)
    
    # 2. Text Message with better spacing
    painter.setOpacity(1.0)
    painter.setPen(QPen(QColor(180, 180, 180)))
    
    # Title Font
    title_font = QFont("Inter", 13, QFont.Weight.Bold)
    if not title_font.exactMatch():
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
    painter.setFont(title_font)
    
    title_text = tr('status.no_videos_title')
    if title_text == 'status.no_videos_title':
         title_text = "Library is empty"
         
    # Position title below icon
    title_top = icon_y_center + icon_size * 0.6
    painter.drawText(
        QRectF(float(rect.left() + 20), float(title_top), float(rect.width() - 40), 30),
        Qt.AlignmentFlag.AlignCenter,
        title_text
    )
    
    # Detailed Instructions Font
    info_font = QFont("Inter", 10)
    if not info_font.exactMatch():
        info_font = QFont("Segoe UI", 10)
    painter.setFont(info_font)
    painter.setPen(QPen(QColor(140, 140, 140)))
    
    text = tr('status.no_videos')
    if text == 'status.no_videos':
        text = "Add a folder in 'Settings'\n\nClick 'Scan' in the 'Library' menu"
    
    # Position text below title with more breathing room
    text_top = title_top + 45
    text_rect = QRectF(float(rect.left() + 40), float(text_top), float(rect.width() - 80), float(rect.height() - text_top))
    
    # Use line spacing for "sparse" look
    option = painter.fontMetrics().boundingRect(text_rect.toRect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, text)
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, text)
