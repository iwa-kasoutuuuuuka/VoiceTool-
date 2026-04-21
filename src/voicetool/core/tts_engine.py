# -*- coding: utf-8 -*-
"""
TTSエンジン。
Coqui XTTS v2によるテキスト音声合成を行う。
"""
import os
import sys
import logging
import tempfile
import traceback
from typing import Optional, Callable

import numpy as np
import torch

logger = logging.getLogger(__name__)


class TTSEngine:
    """Coqui XTTS v2 音声合成エンジン"""

    def __init__(self, models_dir: str):
        """
        Args:
            models_dir: モデルディレクトリのパス
        """
        self.models_dir = models_dir
        self.tts = None
        self.device = "cpu"
        self.model_loaded = False
        self.sample_rate = 24000  # XTTS v2のサンプルレート

    def detect_device(self) -> str:
        """利用可能なデバイスを検出"""
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"GPU検出: {gpu_name} (VRAM: {vram:.1f}GB)")
        else:
            device = "cpu"
            logger.info("GPUが見つかりません。CPUモードで動作します（低速）。")
        return device

    def load_model(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        XTTS v2モデルを読み込む。
        
        Args:
            progress_callback: 進捗メッセージコールバック
        """
        try:
            if progress_callback:
                progress_callback("デバイスを検出中...")

            self.device = self.detect_device()

            if progress_callback:
                progress_callback("TTSモデルを読み込み中 (初回は自動ダウンロード)...")

            # TTS_HOMEを設定してモデルのキャッシュ先を制御
            os.environ["COQUI_TOS_AGREED"] = "1"
            os.environ["TTS_HOME"] = self.models_dir

            from TTS.api import TTS

            self.tts = TTS(
                "tts_models/multilingual/multi-dataset/xtts_v2"
            ).to(self.device)

            self.model_loaded = True
            logger.info(f"TTSモデル読み込み完了 (デバイス: {self.device})")

            if progress_callback:
                progress_callback(f"TTSモデル準備完了 (デバイス: {self.device})")

        except Exception as e:
            logger.error(f"TTSモデル読み込み失敗: {e}")
            logger.error(traceback.format_exc())
            self.model_loaded = False
            raise

    def synthesize(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ja",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        テキストから音声を合成。
        
        Args:
            text: 合成するテキスト
            speaker_wav: リファレンス音声のパス
            language: 言語コード（"ja" or "en"）
            output_path: 出力ファイルパス（Noneなら一時ファイル）
            progress_callback: 進捗コールバック
        
        Returns:
            生成された音声ファイルのパス
        
        Raises:
            RuntimeError: モデル未読込
            FileNotFoundError: リファレンス音声が見つからない
        """
        if not self.model_loaded or self.tts is None:
            raise RuntimeError("TTSモデルが読み込まれていません")

        if not os.path.exists(speaker_wav):
            raise FileNotFoundError(f"リファレンス音声が見つかりません: {speaker_wav}")

        if not text.strip():
            raise ValueError("テキストが空です")

        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav", prefix="tts_")

        try:
            if progress_callback:
                progress_callback(f"音声合成中: {text[:30]}...")

            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language,
            )

            if not os.path.exists(output_path):
                raise RuntimeError("音声ファイルの生成に失敗しました")

            logger.info(f"音声合成完了: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"音声合成エラー: {e}")
            raise

    def get_sample_rate(self) -> int:
        """サンプルレートを返す"""
        return self.sample_rate

    def is_ready(self) -> bool:
        """モデルが使用可能"""
        return self.model_loaded and self.tts is not None

    def unload(self):
        """モデルをアンロード"""
        if self.tts is not None:
            del self.tts
            self.tts = None
            self.model_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("TTSモデルをアンロードしました")
