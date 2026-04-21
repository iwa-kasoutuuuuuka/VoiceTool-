# -*- coding: utf-8 -*-
"""
ツールバー。
ファイル操作・再生・書き出し・リファレンス音声のUI。ドラッグ＆ドロップにも対応。
"""
import os
from PyQt6.QtWidgets import (
    QToolBar, QWidget, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont

from voicetool.ui.styles import COLORS


class ReferenceAudioWidget(QWidget):
    """リファレンス音声表示・ドロップ領域"""

    file_selected = pyqtSignal(str)  # ファイルパス

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._file_path = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        icon_label = QLabel("🎤")
        layout.addWidget(icon_label)

        self.path_label = QLabel("リファレンス音声をドロップ")
        self.path_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            padding: 4px 8px;
            background-color: {COLORS['bg_input']};
            border: 2px dashed {COLORS['border']};
            border-radius: 6px;
            min-width: 200px;
        """)
        layout.addWidget(self.path_label)

        browse_btn = QPushButton("参照...")
        browse_btn.setFixedHeight(28)
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn)

    def _browse(self):
        """ファイル選択ダイアログ"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "リファレンス音声を選択",
            "",
            "音声ファイル (*.wav *.mp3);;WAVファイル (*.wav);;MP3ファイル (*.mp3)"
        )
        if path:
            self.set_file(path)

    def set_file(self, path: str):
        """ファイルを設定"""
        self._file_path = path
        name = os.path.basename(path)
        self.path_label.setText(f"🎤 {name}")
        self.path_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            padding: 4px 8px;
            background-color: {COLORS['bg_input']};
            border: 2px solid {COLORS['accent']};
            border-radius: 6px;
            min-width: 200px;
        """)
        self.file_selected.emit(path)

    def get_file(self) -> str:
        return self._file_path

    def dragEnterEvent(self, event: QDragEnterEvent):
        """ドラッグ開始時"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile().lower()
                if path.endswith((".wav", ".mp3")):
                    event.acceptProposedAction()
                    self.path_label.setStyleSheet(f"""
                        color: {COLORS['accent']};
                        padding: 4px 8px;
                        background-color: {COLORS['bg_tertiary']};
                        border: 2px dashed {COLORS['accent']};
                        border-radius: 6px;
                        min-width: 200px;
                    """)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        """ドラッグ離脱時"""
        if self._file_path:
            self.path_label.setStyleSheet(f"""
                color: {COLORS['text_primary']};
                padding: 4px 8px;
                background-color: {COLORS['bg_input']};
                border: 2px solid {COLORS['accent']};
                border-radius: 6px;
                min-width: 200px;
            """)
        else:
            self.path_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                padding: 4px 8px;
                background-color: {COLORS['bg_input']};
                border: 2px dashed {COLORS['border']};
                border-radius: 6px;
                min-width: 200px;
            """)

    def dropEvent(self, event: QDropEvent):
        """ドロップ時"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith((".wav", ".mp3")):
                self.set_file(path)
                event.acceptProposedAction()


class ToolBar(QToolBar):
    """メインツールバー"""

    # シグナル
    new_project = pyqtSignal()
    open_project = pyqtSignal()
    save_project = pyqtSignal()
    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    generate_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    reference_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("メインツールバー", parent)
        self.setMovable(False)
        self._setup_ui()

    def _setup_ui(self):
        # === ファイル操作 ===
        self.new_action = QAction("📄 新規", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.setToolTip("新規プロジェクト (Ctrl+N)")
        self.new_action.triggered.connect(self.new_project.emit)
        self.addAction(self.new_action)

        self.open_action = QAction("📂 開く", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setToolTip("プロジェクトを開く (Ctrl+O)")
        self.open_action.triggered.connect(self.open_project.emit)
        self.addAction(self.open_action)

        self.save_action = QAction("💾 保存", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setToolTip("プロジェクトを保存 (Ctrl+S)")
        self.save_action.triggered.connect(self.save_project.emit)
        self.addAction(self.save_action)

        self.addSeparator()

        # === リファレンス音声 ===
        self.ref_widget = ReferenceAudioWidget()
        self.ref_widget.file_selected.connect(self.reference_changed.emit)
        self.addWidget(self.ref_widget)

        self.addSeparator()

        # === 生成・再生 ===
        self.generate_action = QAction("🏗️ 生成", self)
        self.generate_action.setToolTip("音声を生成")
        self.generate_action.triggered.connect(self.generate_clicked.emit)
        self.addAction(self.generate_action)

        self.play_action = QAction("▶ 再生", self)
        self.play_action.setShortcut("Space")
        self.play_action.setToolTip("再生 / 停止 (Space)")
        self.play_action.triggered.connect(self.play_clicked.emit)
        self.addAction(self.play_action)

        self.stop_action = QAction("⏹ 停止", self)
        self.stop_action.setToolTip("再生を停止")
        self.stop_action.triggered.connect(self.stop_clicked.emit)
        self.addAction(self.stop_action)

        self.addSeparator()

        # === 書き出し ===
        self.export_action = QAction("📦 書き出し", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.setToolTip("音声ファイルを書き出し (Ctrl+E)")
        self.export_action.triggered.connect(self.export_clicked.emit)
        self.addAction(self.export_action)

    def set_reference_audio(self, path: str):
        """リファレンス音声を設定"""
        if path:
            self.ref_widget.set_file(path)

    def get_reference_audio(self) -> str:
        """リファレンス音声パスを取得"""
        return self.ref_widget.get_file()
