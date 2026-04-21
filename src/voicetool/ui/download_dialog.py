# -*- coding: utf-8 -*-
"""
ダウンロード進捗ダイアログ。
起動時の依存関係ダウンロードUIを表示する。
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QTextEdit, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from voicetool.ui.styles import COLORS
from voicetool.core.dependency_manager import DependencyManager, Dependency

from typing import List


class DownloadWorker(QThread):
    """ダウンロード処理ワーカー（スレッド）"""

    progress = pyqtSignal(str, int, int)   # (status, downloaded, total)
    item_started = pyqtSignal(str)          # (dependency_name)
    item_finished = pyqtSignal(str)         # (dependency_name)
    error = pyqtSignal(str, str)            # (dependency_name, error_message)
    all_finished = pyqtSignal()

    def __init__(self, manager: DependencyManager, missing: List[Dependency]):
        super().__init__()
        self.manager = manager
        self.missing = missing

    def run(self):
        for dep in self.missing:
            self.item_started.emit(dep.name)
            try:
                def progress_cb(downloaded, total, status):
                    self.progress.emit(status, downloaded, total)

                self.manager.install_dependency(dep, progress_callback=progress_cb)
                self.item_finished.emit(dep.name)

            except Exception as e:
                self.error.emit(dep.name, str(e))

        self.all_finished.emit()


class DownloadDialog(QDialog):
    """依存関係ダウンロード進捗ダイアログ"""

    def __init__(self, manager: DependencyManager, missing: List[Dependency], parent=None):
        super().__init__(parent)
        self.manager = manager
        self.missing = missing
        self.success = False
        self.errors = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("セットアップ")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 標題
        title = QLabel("📦 必要なファイルをセットアップしています")
        title.setFont(QFont("Yu Gothic UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 説明
        desc = QLabel(
            f"以下の {len(self.missing)} 個のコンポーネントをダウンロードします。\n"
            "インターネット接続が必要です。"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(desc)

        # 不足コンポーネント一覧
        items_text = "  ".join([f"• {dep.name}" for dep in self.missing])
        items_label = QLabel(items_text)
        items_label.setStyleSheet(f"""
            color: {COLORS['text_accent']};
            padding: 8px;
            background-color: {COLORS['bg_input']};
            border-radius: 6px;
        """)
        items_label.setWordWrap(True)
        layout.addWidget(items_label)

        # 現在のアイテム
        self.current_label = QLabel("準備中...")
        self.current_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        layout.addWidget(self.current_label)

        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # ステータスラベル
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self.status_label)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                font-family: Consolas, monospace;
                font-size: 11px;
            }}
        """)
        layout.addWidget(self.log_text)

        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.close_btn = QPushButton("閉じる")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def start_download(self):
        """ダウンロードを開始"""
        self.worker = DownloadWorker(self.manager, self.missing)
        self.worker.progress.connect(self._on_progress)
        self.worker.item_started.connect(self._on_item_started)
        self.worker.item_finished.connect(self._on_item_finished)
        self.worker.error.connect(self._on_error)
        self.worker.all_finished.connect(self._on_all_finished)
        self.worker.start()

    def _on_progress(self, status: str, downloaded: int, total: int):
        """進捗更新"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(
                f"{status}  ({mb_done:.1f} / {mb_total:.1f} MB)"
            )
        else:
            self.status_label.setText(status)

    def _on_item_started(self, name: str):
        """アイテムのダウンロード開始"""
        self.current_label.setText(f"📥 {name} をダウンロード中...")
        self.log_text.append(f"開始: {name}")
        self.progress_bar.setValue(0)

    def _on_item_finished(self, name: str):
        """アイテムのダウンロード完了"""
        self.log_text.append(f"✅ 完了: {name}")

    def _on_error(self, name: str, error: str):
        """エラー発生"""
        self.errors.append(f"{name}: {error}")
        self.log_text.append(f"❌ エラー: {name} — {error}")
        self.current_label.setText(f"❌ {name} のダウンロードに失敗")
        self.current_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 600;")

    def _on_all_finished(self):
        """全てのダウンロード完了"""
        self.close_btn.setEnabled(True)

        if not self.errors:
            self.success = True
            self.current_label.setText("✅ セットアップ完了！")
            self.current_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: 600;")
            self.progress_bar.setValue(100)
        else:
            self.success = False
            self.current_label.setText(f"⚠️ {len(self.errors)} 個のエラーがあります")
            self.current_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: 600;")
