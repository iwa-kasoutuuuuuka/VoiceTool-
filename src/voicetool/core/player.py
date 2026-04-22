# -*- coding: utf-8 -*-
"""
音声再生エンジン。
sounddeviceを使用したリアルタイム音声再生。
"""
import os
import threading
import logging
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger(__name__)


class AudioPlayer:
    """音声再生エンジン"""

    def __init__(self):
        self._stream = None
        self._data: Optional[np.ndarray] = None
        self._sample_rate: int = 24000
        self._position: int = 0  # 再生位置（サンプル数）
        self._playing: bool = False
        self._lock = threading.Lock()
        self._on_position_changed: Optional[Callable[[float], None]] = None
        self._on_playback_finished: Optional[Callable[[], None]] = None

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def position_seconds(self) -> float:
        """現在の再生位置（秒）"""
        if self._sample_rate > 0:
            return self._position / self._sample_rate
        return 0.0

    @property
    def duration_seconds(self) -> float:
        """音声の長さ（秒）"""
        if self._data is not None and self._sample_rate > 0:
            return len(self._data) / self._sample_rate
        return 0.0

    def set_callbacks(
        self,
        on_position_changed: Optional[Callable[[float], None]] = None,
        on_playback_finished: Optional[Callable[[], None]] = None,
    ):
        """
        コールバックを設定。
        注意: これらのコールバックはオーディオ処理用のリアルタイムスレッドから直接呼び出されます。
        UI操作を行う場合は、必ずメインスレッド（Qtのシグナル送信など）を介してください。
        """
        self._on_position_changed = on_position_changed
        self._on_playback_finished = on_playback_finished

    def load(self, audio_path: str):
        """音声ファイルを読み込む"""
        import soundfile as sf

        self.stop()

        data, sr = sf.read(audio_path)
        # モノラルに変換
        if data.ndim > 1:
            data = data.mean(axis=1)
        # float32に変換
        self._data = data.astype(np.float32)
        self._sample_rate = sr
        self._position = 0
        logger.info(f"音声読み込み: {audio_path} ({sr}Hz, {len(data)/sr:.1f}秒)")

    def load_multiple(self, audio_paths: list):
        """複数の音声ファイルを連結して読み込む"""
        import soundfile as sf

        self.stop()

        all_data = []
        target_sr = None

        for path in audio_paths:
            if not path or not os.path.exists(path):
                continue
            data, sr = sf.read(path)
            if data.ndim > 1:
                data = data.mean(axis=1)
            if target_sr is None:
                target_sr = sr
            all_data.append(data.astype(np.float32))

        if all_data:
            self._data = np.concatenate(all_data)
            self._sample_rate = target_sr or 24000
            self._position = 0

    def play(self):
        """再生開始"""
        if self._data is None:
            logger.warning("再生する音声がありません")
            return

        import sounddevice as sd

        self.stop()

        with self._lock:
            self._playing = True
            self._position = 0

        def callback(outdata, frames, time, status):
            with self._lock:
                if not self._playing or self._data is None:
                    outdata[:] = 0
                    raise sd.CallbackStop()

                end = self._position + frames
                if end > len(self._data):
                    remaining = len(self._data) - self._position
                    outdata[:remaining, 0] = self._data[self._position:len(self._data)]
                    outdata[remaining:] = 0
                    self._position = len(self._data)
                    self._playing = False
                    raise sd.CallbackStop()
                else:
                    outdata[:, 0] = self._data[self._position:end]
                    self._position = end

                if self._on_position_changed:
                    pos_sec = self._position / self._sample_rate
                    self._on_position_changed(pos_sec)

        def finished_callback():
            with self._lock:
                self._playing = False
            if self._on_playback_finished:
                self._on_playback_finished()

        try:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=1,
                callback=callback,
                finished_callback=finished_callback,
                blocksize=1024,
            )
            self._stream.start()
            logger.info("再生開始")
        except Exception as e:
            logger.error(f"再生エラー: {e}")
            self._playing = False

    def stop(self):
        """再生停止（確実にリソースを解放）"""
        with self._lock:
            self._playing = False

        if self._stream is not None:
            try:
                if self._stream.active:
                    self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"ストリームクローズ中の軽微なエラー: {e}")
            finally:
                self._stream = None
                self._position = 0
                logger.info("再生停止")

    def get_waveform_data(self) -> Optional[np.ndarray]:
        """波形データを返す"""
        return self._data

    def get_sample_rate(self) -> int:
        """サンプルレートを返す"""
        return self._sample_rate
