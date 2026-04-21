# -*- coding: utf-8 -*-
"""
波形描画ウィジェット。
numpy配列の音声波形をQPainterで描画する。
"""
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QPainterPath

from voicetool.ui.styles import COLORS


class WaveformWidget(QWidget):
    """波形描画ウィジェット"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: np.ndarray = np.array([])
        self._sample_rate: int = 24000
        self._cursor_position: float = -1.0  # 再生カーソル位置（秒）
        self._downsample_cache: np.ndarray = np.array([])
        self._cache_width: int = 0
        self.setMinimumHeight(60)

    def set_data(self, data: np.ndarray, sample_rate: int = 24000):
        """波形データをセット"""
        if data.ndim > 1:
            data = data.mean(axis=1)
        self._data = data.astype(np.float32)
        self._sample_rate = sample_rate
        self._cache_width = 0  # キャッシュ無効化
        self.update()

    def set_cursor(self, position_seconds: float):
        """再生カーソル位置を設定"""
        self._cursor_position = position_seconds
        self.update()

    def clear(self):
        """波形データをクリア"""
        self._data = np.array([])
        self._cursor_position = -1.0
        self._cache_width = 0
        self.update()

    def _downsample(self, width: int) -> np.ndarray:
        """描画用にダウンサンプリング"""
        if len(self._data) == 0:
            return np.array([])

        if self._cache_width == width and len(self._downsample_cache) > 0:
            return self._downsample_cache

        n = len(self._data)
        if n <= width * 2:
            self._downsample_cache = self._data
            self._cache_width = width
            return self._downsample_cache

        # ブロックごとにmin/maxを取ってエンベロープを描く
        block_size = max(1, n // width)
        blocks = n // block_size
        trimmed = self._data[:blocks * block_size].reshape(blocks, block_size)
        mins = trimmed.min(axis=1)
        maxs = trimmed.max(axis=1)
        envelope = np.empty(blocks * 2)
        envelope[0::2] = mins
        envelope[1::2] = maxs
        self._downsample_cache = envelope
        self._cache_width = width
        return envelope

    def paintEvent(self, event):
        """波形を描画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        bg_color = QColor(COLORS["waveform_bg"])
        painter.fillRect(0, 0, w, h, bg_color)

        # センターライン
        center_y = h / 2
        pen = QPen(QColor(COLORS["border"]), 1)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.drawLine(0, int(center_y), w, int(center_y))

        if len(self._data) == 0:
            painter.setPen(QColor(COLORS["text_secondary"]))
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                "波形なし"
            )
            painter.end()
            return

        # 波形データのダウンサンプリング
        samples = self._downsample(w)
        n = len(samples)
        if n == 0:
            painter.end()
            return

        # 階調
        gradient = QLinearGradient(0, 0, 0, h)
        waveform_color = QColor(COLORS["waveform"])
        gradient.setColorAt(0.0, QColor(waveform_color.red(), waveform_color.green(), waveform_color.blue(), 200))
        gradient.setColorAt(0.5, QColor(waveform_color.red(), waveform_color.green(), waveform_color.blue(), 255))
        gradient.setColorAt(1.0, QColor(waveform_color.red(), waveform_color.green(), waveform_color.blue(), 200))

        # 波形パス
        path = QPainterPath()
        x_scale = w / n
        amp_scale = h * 0.45  # 振幅方向のスケール

        # 最大振幅で正規化
        max_amp = max(np.abs(samples).max(), 1e-6)
        normalized = samples / max_amp

        path.moveTo(0, center_y - normalized[0] * amp_scale)
        for i in range(1, n):
            x = i * x_scale
            y = center_y - normalized[i] * amp_scale
            path.lineTo(x, y)

        # 描画
        pen = QPen(waveform_color, 1)
        painter.setPen(pen)
        painter.drawPath(path)

        # 波形の塗りつぶし（半透明）
        fill_color = QColor(waveform_color)
        fill_color.setAlpha(40)
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, center_y)
        fill_path.lineTo(0, center_y)
        fill_path.closeSubpath()
        painter.fillPath(fill_path, fill_color)

        # 再生カーソル
        if self._cursor_position >= 0:
            total_duration = len(self._data) / self._sample_rate
            if total_duration > 0:
                cursor_x = (self._cursor_position / total_duration) * w
                pen = QPen(QColor(COLORS["cursor"]), 2)
                painter.setPen(pen)
                painter.drawLine(int(cursor_x), 0, int(cursor_x), h)

                # カーソルヘッド（三角形）
                head_size = 6
                head_path = QPainterPath()
                head_path.moveTo(cursor_x - head_size, 0)
                head_path.lineTo(cursor_x + head_size, 0)
                head_path.lineTo(cursor_x, head_size)
                head_path.closeSubpath()
                painter.fillPath(head_path, QColor(COLORS["cursor"]))

        painter.end()
