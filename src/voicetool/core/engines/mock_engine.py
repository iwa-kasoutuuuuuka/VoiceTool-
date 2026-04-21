# -*- coding: utf-8 -*-
"""
Mock エンジン。
テスト用のダミーエンジン。実際の AI は使用せず、即座にダミー音声を生成します。
"""
import os
import time
import numpy as np
import soundfile as sf
from typing import Optional, Callable
from voicetool.core.engine_base import BaseTTSEngine

class MockEngine(BaseTTSEngine):
    """
    テスト用モックエンジン。
    AIモデルをロードせず、1kHzのサイン波を生成して動作を模倣します。
    """

    def __init__(self, models_dir: str):
        self._is_ready = False
        self.sample_rate = 24000

    def load_model(self, progress_callback: Optional[Callable[[str], None]] = None):
        if progress_callback: progress_callback("Mockモデルをロード中...")
        time.sleep(1)  # ロード中を模倣
        self._is_ready = True
        if progress_callback: progress_callback("Mockエンジン準備完了")

    def synthesize(
        self,
        text: str,
        speaker_wav: str,
        language: str = "ja",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        if not self._is_ready: raise RuntimeError("Mockエンジン未起動")
        
        if progress_callback: progress_callback(f"Mock合成中: {text[:10]}...")
        time.sleep(0.5) # 合成中を模倣

        if output_path is None:
            output_path = os.path.join(os.getcwd(), "temp", f"mock_{int(time.time())}.wav")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 1秒のサイン波（ダミー音声）を生成
        dur = 1.0
        t = np.linspace(0, dur, int(self.sample_rate * dur), False)
        audio = np.sin(2 * np.pi * 1000 * t) * 0.5
        sf.write(output_path, audio, self.sample_rate)
        
        return output_path

    def is_ready(self) -> bool:
        return self._is_ready

    def get_sample_rate(self) -> int:
        return self.sample_rate

    def unload(self):
        self._is_ready = False
