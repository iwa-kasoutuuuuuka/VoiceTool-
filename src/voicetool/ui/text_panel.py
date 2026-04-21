# -*- coding: utf-8 -*-
"""
テキスト入力パネル。
改行ごとにセグメントを分割するテキストエリア。
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor

from voicetool.ui.styles import COLORS


class TextPanel(QWidget):
    """テキスト入力パネル（左パネル）"""

    # テキスト変更シグナル
    text_changed = pyqtSignal(str)
    # セグメント選択シグナル（行番号）
    segment_selected = pyqtSignal(int)
    # 言語変更シグナル
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._block_signals = False

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ヘッダー
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("📝 テキスト")
        title.setObjectName("label_section")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 言語選択
        lang_label = QLabel("言語")
        lang_label.setObjectName("label_param")
        header_layout.addWidget(lang_label)

        self.language_combo = QComboBox()
        self.language_combo.addItem("日本語", "ja")
        self.language_combo.addItem("English", "en")
        self.language_combo.setFixedWidth(100)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        header_layout.addWidget(self.language_combo)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        header_widget.setFixedHeight(36)
        layout.addWidget(header_widget)

        # テキストエリア
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "ここにテキストを入力してください...\n"
            "改行ごとに1つのセグメントになります。"
        )
        self.text_edit.setAcceptRichText(False)
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.cursorPositionChanged.connect(self._on_cursor_moved)
        layout.addWidget(self.text_edit)

        # セグメント情報
        self.info_label = QLabel("0 セグメント")
        self.info_label.setObjectName("label_param")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setFixedHeight(24)
        self.info_label.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            border-top: 1px solid {COLORS['border']};
            padding: 2px;
        """)
        layout.addWidget(self.info_label)

    def _on_text_changed(self):
        """テキスト変更時"""
        if self._block_signals:
            return
        text = self.text_edit.toPlainText()
        lines = [l for l in text.split("\n") if l.strip()]
        self.info_label.setText(f"{len(lines)} セグメント")
        self.text_changed.emit(text)

    def _on_cursor_moved(self):
        """カーソル移動時 — 現在行に対応するセグメントを選択"""
        cursor = self.text_edit.textCursor()
        line = cursor.blockNumber()
        self.segment_selected.emit(line)

    def _on_language_changed(self, index: int):
        """言語変更時"""
        lang = self.language_combo.currentData()
        self.language_changed.emit(lang)

    def set_text(self, text: str):
        """テキストを設定（シグナルを発生させない）"""
        self._block_signals = True
        self.text_edit.setPlainText(text)
        lines = [l for l in text.split("\n") if l.strip()]
        self.info_label.setText(f"{len(lines)} セグメント")
        self._block_signals = False

    def get_text(self) -> str:
        """テキストを取得"""
        return self.text_edit.toPlainText()

    def get_language(self) -> str:
        """選択中の言語を取得"""
        return self.language_combo.currentData()

    def set_language(self, lang: str):
        """言語を設定"""
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == lang:
                self.language_combo.setCurrentIndex(i)
                break

    def highlight_segment(self, index: int):
        """指定セグメントの行をハイライト"""
        text = self.text_edit.toPlainText()
        lines = text.split("\n")
        if 0 <= index < len(lines):
            self._block_signals = True
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(index):
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            # 行を選択
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            self.text_edit.setTextCursor(cursor)
            self._block_signals = False
