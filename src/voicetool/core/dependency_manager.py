# -*- coding: utf-8 -*-
"""
依存関係管理。モデル・バイナリの存在チェックと自動ダウンロードを行う。
"""
import os
import sys
import zipfile
import urllib.request
import shutil
import logging
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """依存関係の定義"""
    name: str           # 表示名
    check_path: str     # 存在チェック対象のパス（相対）
    download_url: str   # ダウンロードURL
    is_archive: bool    # zip等のアーカイブか
    extract_to: str     # 展開先（相対パス）
    file_in_archive: str = ""  # アーカイブ内のファイルパス（単体抽出用）


class DependencyManager:
    """依存関係の自動ダウンロード管理"""

    # ffmpegダウンロードURL（gyan.dev の essentials ビルド）
    FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    # rubberbandダウンロードURL
    RUBBERBAND_URL = (
        "https://breakfastquay.com/files/releases/"
        "rubberband-3.3.0-gpl-executable-windows.zip"
    )

    MAX_RETRIES = 3

    def __init__(self, app_dir: str):
        """
        Args:
            app_dir: アプリケーションのルートディレクトリ
        """
        self.app_dir = app_dir
        self.dependencies = self._define_dependencies()

    def _define_dependencies(self) -> List[Dependency]:
        """チェックする依存関係を定義"""
        return [
            Dependency(
                name="FFmpeg",
                check_path=os.path.join("bin", "ffmpeg.exe"),
                download_url=self.FFMPEG_URL,
                is_archive=True,
                extract_to="bin",
                file_in_archive="ffmpeg.exe",
            ),
            Dependency(
                name="Rubberband",
                check_path=os.path.join("bin", "rubberband.exe"),
                download_url=self.RUBBERBAND_URL,
                is_archive=True,
                extract_to="bin",
                file_in_archive="rubberband.exe",
            ),
        ]

    def check_missing(self) -> List[Dependency]:
        """不足している依存関係を返す"""
        missing = []
        for dep in self.dependencies:
            full_path = os.path.join(self.app_dir, dep.check_path)
            if not os.path.exists(full_path):
                missing.append(dep)
                logger.info(f"不足: {dep.name} ({full_path})")
            else:
                logger.info(f"OK: {dep.name} ({full_path})")
        return missing

    def check_xtts_model(self) -> bool:
        """XTTS v2モデルの存在チェック"""
        models_dir = os.path.join(self.app_dir, "models")
        tts_home_dir = models_dir

        patterns = [
            os.path.join(models_dir, "xtts_v2"),
            os.path.join(tts_home_dir, "tts_models--multilingual--multi-dataset--xtts_v2"),
        ]

        for pattern in patterns:
            if os.path.isdir(pattern):
                for f in os.listdir(pattern):
                    if f.endswith(".pth") or f == "config.json":
                        return True
        return False

    def download_file(
        self,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> str:
        """ファイルをダウンロード"""
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if progress_callback:
                    progress_callback(0, 0, f"ダウンロード中... (試行 {attempt}/{self.MAX_RETRIES})")

                req = urllib.request.Request(url)
                req.add_header("User-Agent", "VoiceTool/1.0")

                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    block_size = 8192

                    with open(dest_path, "wb") as f:
                        while True:
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_size, "ダウンロード中...")

                logger.info(f"ダウンロード完了: {url} -> {dest_path}")
                return dest_path

            except Exception as e:
                last_error = e
                logger.warning(f"ダウンロード失敗 (試行 {attempt}): {e}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)

        raise RuntimeError(
            f"ダウンロードに失敗しました（{self.MAX_RETRIES}回試行）: {last_error}"
        )

    def extract_archive(
        self,
        archive_path: str,
        extract_to: str,
        file_in_archive: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """ZIPアーカイブを展開"""
        if progress_callback:
            progress_callback(0, 0, "展開中...")

        os.makedirs(extract_to, exist_ok=True)

        with zipfile.ZipFile(archive_path, "r") as zf:
            if file_in_archive:
                # 特定ファイルのみ抽出
                target_files = [
                    n for n in zf.namelist()
                    if n.endswith(file_in_archive) and not n.endswith("/")
                ]
                if not target_files:
                    raise FileNotFoundError(
                        f"アーカイブ内に {file_in_archive} が見つかりません"
                    )

                for tf in target_files:
                    data = zf.read(tf)
                    dest = os.path.join(extract_to, os.path.basename(tf))
                    with open(dest, "wb") as f:
                        f.write(data)
                    logger.info(f"抽出: {tf} -> {dest}")
            else:
                zf.extractall(extract_to)

        if progress_callback:
            progress_callback(1, 1, "展開完了")

    def install_dependency(
        self,
        dep: Dependency,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """依存関係をインストール"""
        temp_dir = os.path.join(self.app_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            filename = os.path.basename(dep.download_url)
            download_path = os.path.join(temp_dir, filename)

            self.download_file(dep.download_url, download_path, progress_callback)

            if dep.is_archive:
                extract_to = os.path.join(self.app_dir, dep.extract_to)
                self.extract_archive(
                    download_path, extract_to, dep.file_in_archive, progress_callback
                )
            else:
                dest = os.path.join(self.app_dir, dep.check_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(download_path, dest)

        finally:
            temp_file = os.path.join(temp_dir, os.path.basename(dep.download_url))
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
