# -*- coding: utf-8 -*-
"""
ログパネル。
処理状況やエラーメッセージを表示する。
"""
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor

from voicetool.ui.styles import COLORS


class LogHandler(logging.Handler, QObject):
    """ログをUIに送信するハンドラー"""
    log_signal = pyqtSignal(str, str)  # (message, level)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg, record.levelname)


class LogPanel(QWidget):
    """ログ表示パネル"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_logging()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ヘッダー
        header = QLabel("📋 ログ")
        header.setObjectName("label_section")
        header.setFixedHeight(28)
        header.setStyleSheet(f"""
            background-color: {COLORS['bg_secondary']};
            padding-left: 8px;
            border-bottom: 1px solid {COLORS['border']};
        """)
        layout.addWidget(header)

        # ログテキスト
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                border: none;
                border-radius: 0;
                font-family: 'Consolas', 'Yu Gothic UI', monospace;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.log_text)

    def _setup_logging(self):
        """ロギングハンドラーを設定"""
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        self.log_handler.log_signal.connect(self._append_log)

        # ルートロガーにハンドラーを追加
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.INFO)

    def _append_log(self, message: str, level: str):
        """ログメッセージを追加"""
        color_map = {
            "ERROR": COLORS["error"],
            "WARNING": COLORS["warning"],
            "INFO": COLORS["text_primary"],
            "DEBUG": COLORS["text_secondary"],
        }
        color = color_map.get(level, COLORS["text_primary"])

        self.log_text.setTextColor(QColor(color))
        self.log_text.append(message)
        # 自動スクロール
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def log(self, message: str, level: str = "INFO"):
        """直接ログを追加"""
        logger = logging.getLogger(__name__)
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
