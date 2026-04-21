# -*- coding: utf-8 -*-
"""
タイムラインパネル。
セグメントの波形をタイムライン上に表示し、選択・編集を行う。
"""
import os
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QLinearGradient

from voicetool.ui.styles import COLORS
from voicetool.core.segment import Segment

from typing import List, Optional


class TimelineCanvas(QWidget):
    """タイムライン描画キャンバス"""

    segment_clicked = pyqtSignal(int)  # セグメントクリック

    # セグメントの最小幅（ピクセル）
    MIN_SEGMENT_WIDTH = 80
    SEGMENT_HEIGHT = 80
    HEADER_HEIGHT = 24
    GAP = 4  # セグメント間のギャップ

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: List[Segment] = []
        self._waveforms: dict = {}  # index -> np.ndarray
        self._selected_index: int = -1
        self._cursor_position: float = -1.0  # 秒
        self._total_duration: float = 0.0
        self._pixels_per_second: float = 100.0
        self.setMinimumHeight(self.SEGMENT_HEIGHT + self.HEADER_HEIGHT + 20)
        self.setMouseTracking(True)

    def set_segments(self, segments: List[Segment]):
        """セグメントリストを設定"""
        self._segments = segments
        self._update_size()
        self.update()

    def set_waveform(self, index: int, data: np.ndarray):
        """セグメントの波形データを設定"""
        if data.ndim > 1:
            data = data.mean(axis=1)
        self._waveforms[index] = data.astype(np.float32)
        self.update()

    def clear_waveforms(self):
        """波形データをクリア"""
        self._waveforms.clear()
        self.update()

    def set_selected(self, index: int):
        """選択セグメントを設定"""
        self._selected_index = index
        self.update()

    def set_cursor(self, position_seconds: float):
        """再生カーソルを設定"""
        self._cursor_position = position_seconds
        self.update()

    def _update_size(self):
        """キャンバスサイズを更新"""
        total_width = self.GAP
        for seg in self._segments:
            duration = max(seg.duration, 0.5)
            w = max(self.MIN_SEGMENT_WIDTH, int(duration * self._pixels_per_second))
            total_width += w + self.GAP

        total_width = max(total_width, self.parent().width() if self.parent() else 600)
        self.setMinimumWidth(total_width)
        self.setFixedWidth(total_width)

    def _get_segment_rect(self, index: int) -> QRectF:
        """セグメントの描画矩形を取得"""
        x = self.GAP
        for i, seg in enumerate(self._segments):
            duration = max(seg.duration, 0.5)
            w = max(self.MIN_SEGMENT_WIDTH, int(duration * self._pixels_per_second))
            if i == index:
                return QRectF(x, self.HEADER_HEIGHT, w, self.SEGMENT_HEIGHT)
            x += w + self.GAP
        return QRectF()

    def mousePressEvent(self, event):
        """クリックでセグメント選択"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for i in range(len(self._segments)):
                rect = self._get_segment_rect(i)
                if rect.contains(pos):
                    self.segment_clicked.emit(i)
                    return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """タイムラインを描画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.fillRect(0, 0, w, h, QColor(COLORS["waveform_bg"]))

        # タイムヘッダー
        painter.fillRect(0, 0, w, self.HEADER_HEIGHT, QColor(COLORS["bg_secondary"]))
        painter.setPen(QColor(COLORS["border"]))
        painter.drawLine(0, self.HEADER_HEIGHT, w, self.HEADER_HEIGHT)

        # 時間目盛り
        painter.setPen(QColor(COLORS["text_secondary"]))
        font = QFont("Consolas", 8)
        painter.setFont(font)

        x_offset = self.GAP
        current_time = 0.0

        for i, seg in enumerate(self._segments):
            duration = max(seg.duration, 0.5)
            seg_width = max(self.MIN_SEGMENT_WIDTH, int(duration * self._pixels_per_second))

            # 時間ラベル
            time_text = f"{current_time:.1f}s"
            painter.drawText(int(x_offset + 4), int(self.HEADER_HEIGHT - 6), time_text)

            current_time += duration + seg.pause_after
            x_offset += seg_width + self.GAP

        # セグメント描画
        x = self.GAP
        for i, seg in enumerate(self._segments):
            duration = max(seg.duration, 0.5)
            seg_width = max(self.MIN_SEGMENT_WIDTH, int(duration * self._pixels_per_second))
            rect = QRectF(x, self.HEADER_HEIGHT + 2, seg_width, self.SEGMENT_HEIGHT - 4)

            # セグメント背景
            is_selected = (i == self._selected_index)
            if is_selected:
                bg = QColor(COLORS["segment_active"])
                border_color = QColor(COLORS["segment_border"])
            else:
                bg = QColor(COLORS["bg_surface"])
                border_color = QColor(COLORS["border"])

            # 角丸の矩形
            path = QPainterPath()
            path.addRoundedRect(rect, 6, 6)
            painter.fillPath(path, bg)
            painter.setPen(QPen(border_color, 1.5 if is_selected else 1))
            painter.drawPath(path)

            # セグメント番号とテキスト
            painter.setPen(QColor(COLORS["text_primary"] if is_selected else COLORS["text_secondary"]))
            font = QFont("Yu Gothic UI", 9)
            font.setBold(is_selected)
            painter.setFont(font)

            text_rect = QRectF(rect.x() + 4, rect.y() + 2, rect.width() - 8, 18)
            display_text = f"#{i+1} {seg.text}"
            if len(display_text) > 15:
                display_text = display_text[:14] + "…"
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_text)

            # 波形描画
            waveform_rect = QRectF(rect.x() + 2, rect.y() + 22, rect.width() - 4, rect.height() - 26)
            self._draw_segment_waveform(painter, i, waveform_rect)

            x += seg_width + self.GAP

        # 再生カーソル
        if self._cursor_position >= 0 and self._segments:
            cursor_x = self._time_to_x(self._cursor_position)
            if cursor_x >= 0:
                pen = QPen(QColor(COLORS["cursor"]), 2)
                painter.setPen(pen)
                painter.drawLine(int(cursor_x), 0, int(cursor_x), h)

        painter.end()

    def _draw_segment_waveform(self, painter: QPainter, index: int, rect: QRectF):
        """セグメントの波形を描画"""
        if index not in self._waveforms:
            painter.setPen(QColor(COLORS["text_secondary"]))
            font = QFont("Yu Gothic UI", 8)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "未生成")
            return

        data = self._waveforms[index]
        if len(data) == 0:
            return

        w = int(rect.width())
        h = rect.height()
        center_y = rect.y() + h / 2

        # ダウンサンプリング
        points_count = max(1, w)
        if len(data) > points_count:
            block = len(data) // points_count
            blocks = len(data) // block
            trimmed = data[:blocks * block].reshape(blocks, block)
            envelope_max = trimmed.max(axis=1)
            envelope_min = trimmed.min(axis=1)
        else:
            envelope_max = data
            envelope_min = data

        max_amp = max(np.abs(data).max(), 1e-6)
        amp_scale = h * 0.4

        # 波形パス
        waveform_color = QColor(COLORS["waveform"])
        pen = QPen(waveform_color, 1)
        painter.setPen(pen)

        n = len(envelope_max)
        x_scale = rect.width() / n

        for i in range(n):
            x = rect.x() + i * x_scale
            y_max = center_y - (envelope_max[i] / max_amp) * amp_scale
            y_min = center_y - (envelope_min[i] / max_amp) * amp_scale
            painter.drawLine(int(x), int(y_max), int(x), int(y_min))

    def _time_to_x(self, time_seconds: float) -> float:
        """時間（秒）をX座標に変換"""
        x = self.GAP
        current_time = 0.0
        for seg in self._segments:
            duration = max(seg.duration, 0.5)
            seg_width = max(self.MIN_SEGMENT_WIDTH, int(duration * self._pixels_per_second))
            seg_end = current_time + duration

            if current_time <= time_seconds <= seg_end:
                progress = (time_seconds - current_time) / duration if duration > 0 else 0
                return x + progress * seg_width

            current_time = seg_end + seg.pause_after
            x += seg_width + self.GAP

        return -1


class TimelinePanel(QWidget):
    """タイムラインパネル（中央パネル）"""

    segment_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ヘッダー
        header = QLabel("🎞️ タイムライン")
        header.setObjectName("label_section")
        header.setFixedHeight(36)
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            padding-left: 8px;
            border-bottom: 1px solid {COLORS['border']};
        """)
        layout.addWidget(header)

        # スクロール可能なタイムラインキャンバス
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS['waveform_bg']};
            }}
        """)

        self.canvas = TimelineCanvas()
        self.canvas.segment_clicked.connect(self.segment_selected.emit)
        self.scroll_area.setWidget(self.canvas)

        layout.addWidget(self.scroll_area)

    def set_segments(self, segments: List[Segment]):
        """セグメントリストを設定"""
        self.canvas.set_segments(segments)

    def set_waveform(self, index: int, data: np.ndarray):
        """セグメントの波形データを設定"""
        self.canvas.set_waveform(index, data)

    def clear_waveforms(self):
        """波形データをクリア"""
        self.canvas.clear_waveforms()

    def set_selected(self, index: int):
        """選択セグメントを設定"""
        self.canvas.set_selected(index)

    def set_cursor(self, position_seconds: float):
        """再生カーソルを設定"""
        self.canvas.set_cursor(position_seconds)
