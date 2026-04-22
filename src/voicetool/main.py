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
    # ROOT_DIR は exe のあるフォルダ (projects, models, logs用)
    ROOT_DIR = os.path.dirname(sys.executable)
    # BUNDLE_DIR はバンドルされたリソースフォルダ (_internal 等)
    BUNDLE_DIR = sys._MEIPASS
    # パッケージのソースは BUNDLE_DIR 内にある
    SRC_DIR = BUNDLE_DIR
else:
    # 通常のスクリプト実行
    PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
    SRC_DIR = os.path.dirname(PACKAGE_DIR)
    ROOT_DIR = os.path.dirname(SRC_DIR)

# ソースディレクトリをsys.pathの最優先に追加
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
    # PyInstaller環境 (_internalフォルダ) と 実行環境 (exeのあるフォルダ) を区別
    bundle_dir = getattr(sys, '_MEIPASS', ROOT_DIR)
    
    # 外部バイナリ（ffmpeg / rubberband）のパス
    # バンドル内 (_internal/bin) を最優先、次いで実行ディレクトリ (bin/) を確認
    internal_bin = os.path.join(bundle_dir, "bin")
    external_bin = os.path.join(ROOT_DIR, "bin")
    
    bin_path = internal_bin if os.path.exists(internal_bin) else external_bin
    os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")

    # TTS モデルのキャッシュ先 (ユーザーデータなので ROOT_DIR)
    models_dir = os.path.join(ROOT_DIR, "models")
    os.environ["TTS_HOME"] = models_dir
    os.environ["COQUI_TOS_AGREED"] = "1"

    # 必要なディレクトリをルートに作成
    for d in ["bin", "models", "projects", "temp", "temp/cache"]:
        os.makedirs(os.path.join(ROOT_DIR, d), exist_ok=True)

    logger.info(f"ROOT_DIR: {ROOT_DIR}")
    logger.info(f"Bundle path: {bundle_dir}")
    logger.info(f"Bin path: {bin_path}")


def check_dependencies():
    """依存関係を確認"""
    from voicetool.core.dependency_manager import DependencyManager

    bundle_dir = getattr(sys, '_MEIPASS', ROOT_DIR)
    # 優先的にバンドル内を探し、なければルートを探すマネージャ
    manager = DependencyManager(bundle_dir)
    missing = manager.check_missing()

    # バンドル内になく、かつルートにもない場合のみ不足と判定
    if missing:
        external_manager = DependencyManager(ROOT_DIR)
        missing = external_manager.check_missing()
        if not missing:
            manager = external_manager

    if not missing:
        logger.info("全依存関係が揃っています")
        return True

    logger.info(f"不足している依存関係: {[d.name for d in missing]}")

    # 大容量（モデル等）のダウンロードが含まれる場合の警告
    has_large_files = any("Model" in d.name for d in missing)
    if has_large_files:
        from PyQt6.QtWidgets import QMessageBox
        ret = QMessageBox.question(
            None,
            "セットアップ",
            "アプリケーションの実行に必要なボイスモデル（約 2GB）が不足しています。\n"
            "ダウンロードを開始してもよろしいですか？\n\n"
            "※インターネット接続環境によっては時間がかかる場合があります。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return False

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
    try:
        setup_environment()

        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtGui import QFont

        app = QApplication(sys.argv)
        app.setApplicationName("VoiceTool")
        app.setApplicationVersion("1.3.0")
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
        
    except Exception as e:
        import traceback
        error_msg = f"アプリケーションの起動中に致命的なエラーが発生しました:\n\n{e}\n\n{traceback.format_exc()}"
        logger.critical(error_msg)
        
        # UIが表示可能であればメッセージボックスを出す
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "起動エラー", f"致命的なエラーが発生しました:\n{e}")
        except:
            pass
            
        sys.exit(1)


if __name__ == "__main__":
    main()
