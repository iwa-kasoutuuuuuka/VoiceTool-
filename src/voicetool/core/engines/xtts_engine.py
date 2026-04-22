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
import numpy as np
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

    def synthesize_stream(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ja",
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """テキストから音声をストリーミング合成し、NumPy チャンクを yield する"""
        if not self.is_ready():
            raise RuntimeError("モデルが読み込まれていません")

        try:
            if progress_callback:
                progress_callback(f"XTTS v2 ストリーミング開始: {text[:20]}...")
            
            # GPTコンテキストなどを考慮したストリーミング推論
            # TTS.api の TTS クラス経由ではなく、内部モデルを直接叩く必要がある場合が多い
            # ここでは一般的な XTTS 呼び出しパターンに合わせる
            
            gpt_cond_latent, speaker_embedding = self.tts.model.get_conditioning_latents(audio_path=[speaker_wav])
            
            chunks = self.tts.model.inference_stream(
                text,
                language,
                gpt_cond_latent,
                speaker_embedding,
                # パラメータはモデルデフォルトを使用
            )
            
            for chunk in chunks:
                # チャンクは通常 torch.Tensor なので NumPy に変換
                if isinstance(chunk, torch.Tensor):
                    yield chunk.cpu().numpy()
                else:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"XTTSストリーミング合成エラー: {e}")
            raise

    def synthesize(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ja",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """非ストリーミング合成（内部でストリーミングを消費してファイル保存）"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav", prefix="xtts_")
            
        import soundfile as sf
        all_chunks = []
        
        for chunk in self.synthesize_stream(text, speaker_wav, language, progress_callback):
            all_chunks.append(chunk)
            
        if not all_chunks:
            raise RuntimeError("音声の生成に失敗しました")
            
        combined = np.concatenate(all_chunks)
        sf.write(output_path, combined, self.sample_rate)
        return output_path

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
