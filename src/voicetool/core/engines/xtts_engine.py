# -*- coding: utf-8 -*-
"""
XTTS v2 エンジン。
BaseTTSEngine を継承し、Coqui XTTS v2 による音声合成を提供します。
"""
import os
import logging
import tempfile
import traceback
from typing import Optional, Callable

import torch
from voicetool.core.engine_base import BaseTTSEngine

logger = logging.getLogger(__name__)

class XTTSv2Engine(BaseTTSEngine):
    """Coqui XTTS v2 音声合成エンジン"""

    def __init__(self, models_dir: str):
        self.models_dir = models_dir
        self.tts = None
        self.device = "cpu"
        self.model_loaded = False
        self.sample_rate = 24000

    def detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load_model(self, progress_callback: Optional[Callable[[str], None]] = None):
        try:
            if progress_callback:
                progress_callback("デバイスを検出中...")
            self.device = self.detect_device()

            if progress_callback:
                progress_callback("XTTS v2 モデルを読み込み中...")

            os.environ["COQUI_TOS_AGREED"] = "1"
            os.environ["TTS_HOME"] = self.models_dir

            from TTS.api import TTS
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            self.model_loaded = True
            
            if progress_callback:
                progress_callback(f"XTTS v2 準備完了 ({self.device})")
        except Exception as e:
            logger.error(f"XTTSモデル読み込み失敗: {e}")
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
        if not self.is_ready():
            raise RuntimeError("モデルが読み込まれていません")

        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav", prefix="xtts_")

        try:
            if progress_callback:
                progress_callback(f"XTTS v2 合成中: {text[:20]}...")
            
            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language,
            )
            return output_path
        except Exception as e:
            logger.error(f"XTTS合成エラー: {e}")
            raise

    def is_ready(self) -> bool:
        return self.model_loaded and self.tts is not None

    def get_sample_rate(self) -> int:
        return self.sample_rate

    def unload(self):
        if self.tts is not None:
            del self.tts
            self.tts = None
            self.model_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("XTTS v2 モデルを解放しました")
