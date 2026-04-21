# -*- coding: utf-8 -*-
"""
パラメータパネル。
セグメントの速さ・ピッチ・音量・長さ・ポーズと感情パラメータのUI。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QDoubleSpinBox, QGroupBox, QScrollArea, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal

from voicetool.ui.styles import COLORS, EMOTION_COLORS
from voicetool.core.segment import Segment, Emotion


class ParamSlider(QWidget):
    """ラベル付きスライダー"""
    value_changed = pyqtSignal(float)

    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        default: float,
        step: float = 0.1,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.suffix = suffix
        self._block = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        # ラベル行
        top = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setObjectName("label_param")
        top.addWidget(self.label)
        top.addStretch()

        self.value_label = QLabel(f"{default:.2f}{suffix}")
        self.value_label.setObjectName("label_param")
        self.value_label.setMinimumWidth(50)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(self.value_label)
        layout.addLayout(top)

        # スライダー + スピンボックス
        slider_row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val / step))
        self.slider.setMaximum(int(max_val / step))
        self.slider.setValue(int(default / step))
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_row.addWidget(self.slider)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setSingleStep(step)
        self.spinbox.setValue(default)
        self.spinbox.setDecimals(2)
        self.spinbox.setFixedWidth(70)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        slider_row.addWidget(self.spinbox)

        layout.addLayout(slider_row)

    def _on_slider_changed(self, val):
        if self._block:
            return
        self._block = True
        value = val * self.step
        self.spinbox.setValue(value)
        self.value_label.setText(f"{value:.2f}{self.suffix}")
        self.value_changed.emit(value)
        self._block = False

    def _on_spinbox_changed(self, val):
        if self._block:
            return
        self._block = True
        self.slider.setValue(int(val / self.step))
        self.value_label.setText(f"{val:.2f}{self.suffix}")
        self.value_changed.emit(val)
        self._block = False

    def set_value(self, val: float):
        """値を設定（シグナル発火なし）"""
        self._block = True
        self.slider.setValue(int(val / self.step))
        self.spinbox.setValue(val)
        self.value_label.setText(f"{val:.2f}{self.suffix}")
        self._block = False

    def get_value(self) -> float:
        return self.spinbox.value()


class EmotionSlider(QWidget):
    """感情パラメータ用カラースライダー"""
    value_changed = pyqtSignal(str, float)  # (emotion_name, value)

    def __init__(self, name: str, display_name: str, color: str, parent=None):
        super().__init__(parent)
        self.emotion_name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.label = QLabel(display_name)
        self.label.setFixedWidth(50)
        self.label.setStyleSheet(f"color: {color}; font-weight: 600;")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['bg_input']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {color};
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {color};
                border-radius: 3px;
                opacity: 0.7;
            }}
        """)
        self.slider.valueChanged.connect(self._on_changed)
        layout.addWidget(self.slider)

        self.value_label = QLabel("0.00")
        self.value_label.setFixedWidth(36)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

    def _on_changed(self, val):
        value = val / 100.0
        self.value_label.setText(f"{value:.2f}")
        self.value_changed.emit(self.emotion_name, value)

    def set_value(self, val: float):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * 100))
        self.value_label.setText(f"{val:.2f}")
        self.slider.blockSignals(False)

    def get_value(self) -> float:
        return self.slider.value() / 100.0


class ParameterPanel(QWidget):
    """パラメータパネル（右パネル）"""

    # パラメータ変更シグナル
    parameter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_segment: int = -1
        self._block_signals = False
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ヘッダー
        header = QLabel("🔹 パラメータ")
        header.setObjectName("label_section")
        header.setFixedHeight(36)
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            padding-left: 8px;
            border-bottom: 1px solid {COLORS['border']};
        """)
        main_layout.addWidget(header)

        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS['bg_surface']};
            }}
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(4)

        # セグメント情報
        self.segment_label = QLabel("セグメント未選択")
        self.segment_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.segment_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            padding: 6px;
            background-color: {COLORS['bg_input']};
            border-radius: 6px;
        """)
        content_layout.addWidget(self.segment_label)

        # 音声パラメータグループ
        voice_group = QGroupBox("🔉 音声パラメータ")
        voice_layout = QVBoxLayout(voice_group)

        self.speed_slider = ParamSlider("速さ", 0.5, 2.0, 1.0, 0.05, "x")
        self.speed_slider.value_changed.connect(self._on_param_changed)
        voice_layout.addWidget(self.speed_slider)

        self.pitch_slider = ParamSlider("ピッチ", -12.0, 12.0, 0.0, 0.5, " st")
        self.pitch_slider.value_changed.connect(self._on_param_changed)
        voice_layout.addWidget(self.pitch_slider)

        self.volume_slider = ParamSlider("音量", -20.0, 20.0, 0.0, 0.5, " dB")
        self.volume_slider.value_changed.connect(self._on_param_changed)
        voice_layout.addWidget(self.volume_slider)

        self.length_slider = ParamSlider("長さ", 0.5, 2.0, 1.0, 0.05, "x")
        self.length_slider.value_changed.connect(self._on_param_changed)
        voice_layout.addWidget(self.length_slider)

        self.pause_slider = ParamSlider("ポーズ", 0.0, 3.0, 0.5, 0.1, " 秒")
        self.pause_slider.value_changed.connect(self._on_param_changed)
        voice_layout.addWidget(self.pause_slider)

        content_layout.addWidget(voice_group)

        # 感情パラメータグループ
        emotion_group = QGroupBox("😊 感情")
        emotion_layout = QVBoxLayout(emotion_group)

        self.emotion_sliders = {}
        emotions = [
            ("happy", "幸せ", EMOTION_COLORS["happy"]),
            ("fun", "楽しみ", EMOTION_COLORS["fun"]),
            ("angry", "怒り", EMOTION_COLORS["angry"]),
            ("sad", "悲しみ", EMOTION_COLORS["sad"]),
        ]
        for name, display, color in emotions:
            slider = EmotionSlider(name, display, color)
            slider.value_changed.connect(self._on_emotion_changed)
            emotion_layout.addWidget(slider)
            self.emotion_sliders[name] = slider

        # 感情リセットボタン
        reset_btn = QPushButton("リセット")
        reset_btn.setFixedHeight(28)
        reset_btn.clicked.connect(self._reset_emotions)
        emotion_layout.addWidget(reset_btn)

        content_layout.addWidget(emotion_group)
        content_layout.addStretch()

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _on_param_changed(self, _=None):
        """パラメータ変更時"""
        if not self._block_signals:
            self.parameter_changed.emit()

    def _on_emotion_changed(self, name: str, value: float):
        """感情パラメータ変更時"""
        if not self._block_signals:
            self.parameter_changed.emit()

    def _reset_emotions(self):
        """感情パラメータをリセット"""
        for slider in self.emotion_sliders.values():
            slider.set_value(0.0)
        self.parameter_changed.emit()

    def load_segment(self, segment: Segment, index: int):
        """セグメントのパラメータを表示"""
        self._block_signals = True
        self._current_segment = index
        self.segment_label.setText(
            f"セグメント {index + 1}: {segment.text[:20]}..."
            if len(segment.text) > 20
            else f"セグメント {index + 1}: {segment.text}"
        )

        self.speed_slider.set_value(segment.speed)
        self.pitch_slider.set_value(segment.pitch)
        self.volume_slider.set_value(segment.volume)
        self.length_slider.set_value(segment.length)
        self.pause_slider.set_value(segment.pause_after)

        self.emotion_sliders["happy"].set_value(segment.emotion.happy)
        self.emotion_sliders["fun"].set_value(segment.emotion.fun)
        self.emotion_sliders["angry"].set_value(segment.emotion.angry)
        self.emotion_sliders["sad"].set_value(segment.emotion.sad)

        self._block_signals = False

    def save_to_segment(self, segment: Segment):
        """現在のパラメータをセグメントに保存"""
        old_key = segment.cache_key("", "")

        segment.speed = self.speed_slider.get_value()
        segment.pitch = self.pitch_slider.get_value()
        segment.volume = self.volume_slider.get_value()
        segment.length = self.length_slider.get_value()
        segment.pause_after = self.pause_slider.get_value()

        segment.emotion = Emotion(
            happy=self.emotion_sliders["happy"].get_value(),
            fun=self.emotion_sliders["fun"].get_value(),
            angry=self.emotion_sliders["angry"].get_value(),
            sad=self.emotion_sliders["sad"].get_value(),
        )

        new_key = segment.cache_key("", "")
        if old_key != new_key:
            # パラメータ変更によりキャッシュ無効
            segment.audio_path = None

    def clear(self):
        """パラメータをクリア"""
        self._current_segment = -1
        self.segment_label.setText("セグメント未選択")
        self._block_signals = True
        self.speed_slider.set_value(1.0)
        self.pitch_slider.set_value(0.0)
        self.volume_slider.set_value(0.0)
        self.length_slider.set_value(1.0)
        self.pause_slider.set_value(0.5)
        for slider in self.emotion_sliders.values():
            slider.set_value(0.0)
        self._block_signals = False
