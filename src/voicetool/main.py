# -*- coding: utf-8 -*-
"""
VoiceTool — 音声編集＋音声合成ツール
メインエントリーポイント

新フォルダ構成対応版:
  Root/
    src/voicetool/
      main.py
    bin/
    models/
    ...
"""
import os
import sys
import logging

# パス設定の取得
if getattr(sys, 'frozen', False):
    # PyInstallerで実行されている場合 (exe)
    # ROOT_DIR は exe のあるフォルダ
    ROOT_DIR = os.path.dirname(sys.executable)
    # ソースは内部のリソースフォルダ（通常 _MEIPASS に展開されるが、今回 src を含めるならそこ）
    PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
    SRC_DIR = os.path.dirname(PACKAGE_DIR)
else:
    # 通常のスクリプト実行
    PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
    SRC_DIR = os.path.dirname(PACKAGE_DIR)
    ROOT_DIR = os.path.dirname(SRC_DIR)

# ソースディレクトリをsys.pathに追加
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("VoiceTool")


def setup_environment():
    """環境変数とパスを設定"""
    # 外部バイナリ（ffmpeg / rubberband）のパス
    bin_dir = os.path.join(ROOT_DIR, "bin")
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    # TTS モデルのキャッシュ先
    models_dir = os.path.join(ROOT_DIR, "models")
    os.environ["TTS_HOME"] = models_dir
    os.environ["COQUI_TOS_AGREED"] = "1"

    # 必要なディレクトリをルートに作成
    for d in ["bin", "models", "projects", "temp", "temp/cache"]:
        os.makedirs(os.path.join(ROOT_DIR, d), exist_ok=True)

    logger.info(f"ROOT_DIR: {ROOT_DIR}")
    logger.info(f"PACKAGE_DIR: {PACKAGE_DIR}")


def check_dependencies():
    """依存関係を確認"""
    from voicetool.core.dependency_manager import DependencyManager

    # 依存関係マネージャにはROOT_DIRを渡す（bin/ などを探すため）
    manager = DependencyManager(ROOT_DIR)
    missing = manager.check_missing()

    if not missing:
        logger.info("全依存関係が揃っています")
        return True

    logger.info(f"不足している依存関係: {[d.name for d in missing]}")

    from voicetool.ui.download_dialog import DownloadDialog
    dialog = DownloadDialog(manager, missing)
    dialog.start_download()
    dialog.exec()

    if not dialog.success:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "セットアップエラー",
            "必要なファイルのダウンロードに失敗しました。\n" + "\n".join(dialog.errors),
        )
        return False

    return True


def generate_spec():
    """仕様書を生成 (docs/配下に)"""
    from voicetool.core.spec_generator import generate_spec as gen

    doc_dir = os.path.join(ROOT_DIR, "docs")
    os.makedirs(doc_dir, exist_ok=True)
    spec_path = os.path.join(doc_dir, "VoiceTool_Spec.txt")
    gen(spec_path)
    logger.info(f"仕様書を更新しました: {spec_path}")


def main():
    """メインエントリーポイント"""
    setup_environment()

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceTool")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")

    font = QFont("Yu Gothic UI", 10)
    app.setFont(font)

    if not check_dependencies():
        sys.exit(1)

    generate_spec()

    from voicetool.ui.main_window import MainWindow
    # メインウィンドウにはROOT_DIRを渡す（projects/などを操作するため）
    window = MainWindow(ROOT_DIR)
    window.show()

    from PyQt6.QtCore import QTimer
    QTimer.singleShot(500, window.load_tts_model)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
