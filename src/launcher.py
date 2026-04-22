import sys
import os

# PyInstaller の展開先 (_internal 等) を取得
if getattr(sys, 'frozen', False):
    # EXE実行時: _internal フォルダ (sys._MEIPASS)
    bundle_dir = sys._MEIPASS
else:
    # スクリプト実行時: src フォルダ
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# パスに追加 (voicetool パッケージを見つけられるようにする)
# 開発環境でもビルド環境でも src/ フォルダをルートとして認識させる
if bundle_dir in sys.path:
    sys.path.remove(bundle_dir)
sys.path.insert(0, bundle_dir)

# メイン関数の呼び出し
from voicetool.main import main

if __name__ == "__main__":
    main()
