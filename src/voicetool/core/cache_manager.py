# -*- coding: utf-8 -*-
"""
キャッシュ管理。同一条件の音声は再生成しないようキャッシュする。
"""
import os
import shutil
from typing import Optional


class CacheManager:
    """音声キャッシュ管理"""

    def __init__(self, cache_dir: str):
        """
        Args:
            cache_dir: キャッシュディレクトリのパス
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get(self, cache_key: str) -> Optional[str]:
        """
        キャッシュからファイルパスを取得。
        
        Args:
            cache_key: キャッシュキー（SHA256ハッシュ）
        
        Returns:
            キャッシュファイルのパス（存在しない場合はNone）
        """
        path = os.path.join(self.cache_dir, f"{cache_key}.wav")
        if os.path.exists(path):
            return path
        return None

    def put(self, cache_key: str, audio_path: str) -> str:
        """
        音声ファイルをキャッシュに保存。
        
        Args:
            cache_key: キャッシュキー
            audio_path: 元の音声ファイルパス
        
        Returns:
            キャッシュファイルのパス
        """
        dest = os.path.join(self.cache_dir, f"{cache_key}.wav")
        if audio_path != dest:
            shutil.copy2(audio_path, dest)
        return dest

    def invalidate(self, cache_key: str):
        """キャッシュを無効化"""
        path = os.path.join(self.cache_dir, f"{cache_key}.wav")
        if os.path.exists(path):
            os.remove(path)

    def clear(self):
        """全キャッシュを削除"""
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)

    def get_size_mb(self) -> float:
        """キャッシュサイズ（MB）を取得"""
        total = 0
        for f in os.listdir(self.cache_dir):
            fp = os.path.join(self.cache_dir, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
        return total / (1024 * 1024)
