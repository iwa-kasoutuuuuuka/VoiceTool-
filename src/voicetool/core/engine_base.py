# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional, Callable
import numpy as np

class BaseTTSEngine(ABC):
    """
    音声合成エンジンの抽象基底クラス。
    新しいエンジンを追加する場合は、このクラスを継承して実装します。
    """

    @abstractmethod
    def load_model(self, progress_callback: Optional[Callable[[str], None]] = None):
        """モデルを読み込む（重い処理）"""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ja",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """テキストから音声を合成し、保存したファイルパスを返す"""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """モデルが読み込まれ、合成可能な状態か"""
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """エンジンの標準サンプルレートを返す"""
        pass

    @abstractmethod
    def unload(self):
        """モデルをメモリから解放する"""
        pass
