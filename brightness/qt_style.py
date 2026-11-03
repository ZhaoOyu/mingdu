"""System-palette styling and compact monochrome symbols for the Qt panel."""
import sys
import math
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from .presentation import RING_START, RING_SWEEP


def blended_color(palette, strength):
    foreground = palette.color(QPalette.ColorRole.WindowText)
    background = palette.color(QPalette.ColorRole.Window)
    return QColor(*(round(f * strength + b * (1 - strength)) for f, b in
                    zip(foreground.getRgb()[:3], background.getRgb()[:3])))


def panel_style(palette):
    role = QPalette.ColorRole
    window = palette.color(role.Window).name()
    foreground = palette.color(role.WindowText).name()
    muted = blended_color(palette, 0.62).name()
    line = blended_color(palette, 0.16).name()
    return f"""
    QMainWindow, QWidget#content {{ background: {window}; color: {foreground}; }}
    QLabel {{ color: {foreground}; background: transparent; }}
    QLabel#hero {{ font-size: 17px; font-weight: bold; }}
    QLabel#muted {{ color: {muted}; font-size: 12px; }}
    QLabel#monitor {{ font-size: 14px; font-weight: bold; }}
    QLabel#value {{ font-size: 18px; font-weight: bold; }}
    QFrame#card {{ background: transparent; border: none; border-bottom: 1px solid {line}; }}
    QFrame#separator {{ border: none; background: {line}; max-height: 1px; }}
    QPushButton {{ padding: 4px 8px; min-height: 22px; }}
    QComboBox {{ min-height: 26px; }}
    QScrollArea {{ border: none; background: {window}; }}
    QTextEdit {{ border: 1px solid {line}; border-radius: 6px; padding: 6px; }}
    """


def symbol_icon(name="sun", color=None):
    color = color or QApplication.palette().color(QPalette.ColorRole.WindowText)
    pixmap = QPixmap(72, 72)
    pixmap.setDevicePixelRatio(3)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if name == "monitor":
        painter.drawRoundedRect(QRectF(3, 4, 18, 13), 1.5, 1.5)
        painter.drawLine(12, 17, 12, 21)
        painter.drawLine(8, 21, 16, 21)
    elif name == "refresh":
        painter.drawArc(QRectF(5, 5, 14, 14), 40 * 16, 290 * 16)
        painter.drawLine(19, 4, 19, 10)
        painter.drawLine(19, 10, 13, 10)
    else:
        painter.drawEllipse(QRectF(8, 8, 8, 8))
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(angle)
            painter.drawLine(0, -8, 0, -10)
            painter.restore()
    painter.end()
    return QIcon(pixmap)


def brightness_icon(summary):
    pixmap = QPixmap(96, 96)
    pixmap.setDevicePixelRatio(4)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QApplication.palette().color(QPalette.ColorRole.WindowText)
    if sys.platform == "darwin":
        color = QColor("black")  # Cocoa template image follows the menu bar appearance.
    rect = QRectF(1.2, 1.2, 21.6, 21.6)
    font = QFont(QApplication.font())
    font.setPixelSize(9 if len(summary.text) > 2 else 11)
    font.setBold(True)
    painter.setFont(font)
    sun = QPainterPath()
    sun.addEllipse(QRectF(10.55, 18.65, 2.9, 2.9))
    for angle in range(0, 360, 45):
        radians = math.radians(angle)
        sun.moveTo(12 + 2.4 * math.cos(radians), 20.1 + 2.4 * math.sin(radians))
        sun.lineTo(12 + 3.8 * math.cos(radians), 20.1 + 3.8 * math.sin(radians))
    if sys.platform != "darwin":
        halo = QColor("white" if color.lightness() < 128 else "black")
        halo.setAlpha(180)
        painter.setPen(QPen(halo, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, round(RING_START * 16), -round(RING_SWEEP * 16))
        path = QPainterPath()
        metrics = painter.fontMetrics()
        path.addText(12 - metrics.horizontalAdvance(summary.text) / 2,
                     10 + (metrics.ascent() - metrics.descent()) / 2, font, summary.text)
        painter.strokePath(path, QPen(halo, 1.2))
        painter.strokePath(sun, QPen(halo, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    track = QColor(color)
    track.setAlphaF(0.28)
    painter.setPen(QPen(track, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawArc(rect, round(RING_START * 16), -round(RING_SWEEP * 16))
    if summary.value is not None and summary.value > 0:
        painter.setPen(QPen(color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, round(RING_START * 16), -round(summary.value * RING_SWEEP / 100 * 16))
    painter.setPen(color)
    painter.drawText(QRectF(1, 2, 22, 16), Qt.AlignmentFlag.AlignCenter, summary.text)
    painter.fillPath(sun, color)
    painter.strokePath(sun, QPen(color, .9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.end()
    icon = QIcon(pixmap)
    icon.setIsMask(sys.platform == "darwin")
    return icon
