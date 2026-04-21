# -*- coding: utf-8 -*-
"""
音声加工パイプライン。
rubberband / ffmpeg / pydub を使った音声の加工処理を行う。
処理順序（仕様書準拠）:
  1. pitch（rubberband）
  2. speed（ffmpeg）
  3. volume（loudnorm）
  4. ポーズ追加
"""
import os
import sys
import subprocess
import tempfile
import logging
import shutil
from typing import Optional

import numpy as np
from voicetool.core.native_dsp_bridge import NativeDSPBridge

logger = logging.getLogger(__name__)


class AudioProcessor:
    """音声加工パイプライン"""

    def __init__(self, bin_dir: str, temp_dir: str):
        """
        Args:
            bin_dir: ffmpeg.exe / rubberband.exe が格納されたディレクトリ
            temp_dir: 一時ファイルディレクトリ
        """
        self.ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")
        self.rubberband_path = os.path.join(bin_dir, "rubberband.exe")
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    def _get_temp_path(self, suffix: str = ".wav") -> str:
        """一時ファイルパスを生成"""
        return tempfile.mktemp(suffix=suffix, dir=self.temp_dir, prefix="proc_")

    def _run_command(self, cmd: list, description: str = ""):
        """外部コマンドを実行（堅牢性強化版）"""
        # 入力ファイルの存在チェック (コマンド内のパスが含まれる場合)
        for arg in cmd:
            if isinstance(arg, str) and (arg.endswith(".wav") or arg.endswith(".mp3")) and not arg.startswith("-"):
                if "proc_" not in arg and not os.path.exists(arg):
                     logger.warning(f"コマンド実行前にファイル不在を確認: {arg}")

        logger.debug(f"コマンド実行 ({description}): {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180, # タイムアウトを少し延長
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if result.returncode != 0:
                err_msg = result.stderr if result.stderr else result.stdout
                logger.error(f"コマンドエラー ({description}): {err_msg}")
                raise RuntimeError(f"{description}に失敗: {err_msg}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"コマンド実行タイムアウト ({description})")
            raise RuntimeError(f"{description}がタイムアウトしました。処理を中断します。")
        except Exception as e:
            logger.error(f"予期せぬコマンド実行エラー ({description}): {e}")
            raise

    def change_pitch(self, input_path: str, semitones: float) -> str:
        """ピッチを変更（rubberband使用）"""
        if abs(semitones) < 0.01:
            return input_path

        if not os.path.exists(self.rubberband_path):
            logger.warning("rubberband.exeが見つかりません。ピッチ変更をスキップ。")
            return input_path

        output_path = self._get_temp_path()
        cmd = [
            self.rubberband_path,
            "--pitch", str(semitones),
            "--realtime",
            input_path,
            output_path,
        ]
        self._run_command(cmd, "ピッチ変更")
        return output_path

    def change_speed(self, input_path: str, speed_factor: float) -> str:
        """速度を変更（ffmpeg atempo使用）"""
        if abs(speed_factor - 1.0) < 0.01:
            return input_path

        if not os.path.exists(self.ffmpeg_path):
            logger.warning("ffmpeg.exeが見つかりません。速度変更をスキップ。")
            return input_path

        output_path = self._get_temp_path()

        # atempoは0.5～2.0の範囲。範囲外はチェーンする
        filters = []
        remaining = speed_factor
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining:.4f}")

        filter_str = ",".join(filters)

        cmd = [
            self.ffmpeg_path,
            "-y", "-i", input_path,
            "-filter:a", filter_str,
            "-acodec", "pcm_s16le",
            output_path,
        ]
        self._run_command(cmd, "速度変更")
        return output_path

    def change_volume(self, input_path: str, volume_db: float) -> str:
        """音量を変更（ネイティブエンジン優先）"""
        if abs(volume_db) < 0.1:
            return input_path

        # ネイティブエンジンの使用を試みる
        if NativeDSPBridge.is_available():
            try:
                import soundfile as sf
                data, sr = sf.read(input_path)
                data = data.astype(np.float32)
                
                if NativeDSPBridge.apply_gain(data, volume_db):
                    output_path = self._get_temp_path()
                    sf.write(output_path, data, sr)
                    return output_path
            except Exception as e:
                logger.warning(f"ネイティブ音量調整失敗、フォールバックします: {e}")

        # フォールバック: ffmpeg
        if not os.path.exists(self.ffmpeg_path):
            logger.warning("ffmpeg.exeが見つかりません。音量変更をスキップ。")
            return input_path

        output_path = self._get_temp_path()
        cmd = [
            self.ffmpeg_path,
            "-y", "-i", input_path,
            "-filter:a", f"volume={volume_db}dB",
            "-acodec", "pcm_s16le",
            output_path,
        ]
        self._run_command(cmd, "音量変更")
        return output_path

    def add_pause(self, input_path: str, pause_seconds: float) -> str:
        """音声の末尾にポーズ（無音）を追加（ネイティブエンジン優先）"""
        if pause_seconds <= 0:
            return input_path

        try:
            import soundfile as sf
            data, sr = sf.read(input_path)
            data = data.astype(np.float32)

            # ネイティブエンジンで連結（自分自身 + 無音）
            silence_samples = int(sr * pause_seconds)
            
            if NativeDSPBridge.is_available():
                result = NativeDSPBridge.concatenate([data], [silence_samples])
                if result is not None:
                    output_path = self._get_temp_path()
                    sf.write(output_path, result, sr)
                    return output_path

            # フォールバック: パイソン実装
            if data.ndim == 1:
                silence = np.zeros(silence_samples, dtype=np.float32)
            else:
                silence = np.zeros((silence_samples, data.shape[1]), dtype=np.float32)

            result = np.concatenate([data, silence])
            output_path = self._get_temp_path()
            sf.write(output_path, result, sr)
            return output_path

        except Exception as e:
            logger.error(f"ポーズ追加エラー: {e}")
            return input_path

    def process_segment(
        self,
        input_path: str,
        pitch_semitones: float = 0.0,
        speed_factor: float = 1.0,
        volume_db: float = 0.0,
        pause_after: float = 0.0,
    ) -> str:
        """セグメントの音声を一括加工。順序: pitch -> speed -> volume -> pause"""
        current = input_path
        temp_files = []

        try:
            # 1. ピッチ変更
            result = self.change_pitch(current, pitch_semitones)
            if result != current:
                temp_files.append(current if current != input_path else None)
                current = result

            # 2. 速度変更
            result = self.change_speed(current, speed_factor)
            if result != current:
                temp_files.append(current if current != input_path else None)
                current = result

            # 3. 音量変更
            result = self.change_volume(current, volume_db)
            if result != current:
                temp_files.append(current if current != input_path else None)
                current = result

            # 4. ポーズ追加
            result = self.add_pause(current, pause_after)
            if result != current:
                temp_files.append(current if current != input_path else None)
                current = result

            return current

        finally:
            # 中間一時ファイルを削除
            for tf in temp_files:
                if tf and tf != input_path and tf != current and os.path.exists(tf):
                    try:
                        os.remove(tf)
                    except Exception:
                        pass

    def concatenate_segments(
        self,
        audio_paths: list,
        output_path: str,
        output_format: str = "wav",
    ) -> str:
        """複数の音声ファイルを連結して出力"""
        if not audio_paths:
            raise ValueError("連結する音声がありません")

        try:
            import soundfile as sf

            all_data = []
            target_sr = None

            for path in audio_paths:
                if not os.path.exists(path):
                    logger.warning(f"スキップ（ファイル不在）: {path}")
                    continue
                data, sr = sf.read(path)
                data = data.astype(np.float32)
                if target_sr is None:
                    target_sr = sr
                
                # モノラルに統一（ネイティブ処理の単純化のため）
                if data.ndim > 1:
                    data = data.mean(axis=1)
                all_data.append(data)

            if not all_data:
                raise ValueError("有効な音声データがありません")

            # ネイティブエンジンで高速連結
            if NativeDSPBridge.is_available():
                combined = NativeDSPBridge.concatenate(all_data, [0] * len(all_data))
            else:
                combined = np.concatenate(all_data)

            if output_format == "mp3":
                temp_wav = self._get_temp_path()
                sf.write(temp_wav, combined, target_sr)
                self._convert_to_mp3(temp_wav, output_path)
                os.remove(temp_wav)
            else:
                sf.write(output_path, combined, target_sr)

            logger.info(f"連結完了: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"連結エラー: {e}")
            raise

    def _convert_to_mp3(self, input_path: str, output_path: str):
        """WAVをMP3に変換"""
        if not os.path.exists(self.ffmpeg_path):
            raise RuntimeError("ffmpegが見つからないためMP3変換できません")

        cmd = [
            self.ffmpeg_path,
            "-y", "-i", input_path,
            "-codec:a", "libmp3lame",
            "-qscale:a", "2",
            output_path,
        ]
        self._run_command(cmd, "MP3変換")

    def convert_to_wav(self, input_path: str) -> str:
        """MP3等をWAVに変換（リファレンス音声用）"""
        if input_path.lower().endswith(".wav"):
            return input_path

        if not os.path.exists(self.ffmpeg_path):
            raise RuntimeError("ffmpegが見つからないため変換できません")

        output_path = self._get_temp_path()
        cmd = [
            self.ffmpeg_path,
            "-y", "-i", input_path,
            "-acodec", "pcm_s16le",
            "-ar", "22050",
            "-ac", "1",
            output_path,
        ]
        self._run_command(cmd, "WAV変換")
        return output_path

    def get_audio_duration(self, audio_path: str) -> float:
        """音声ファイルの長さ（秒）を取得"""
        try:
            import soundfile as sf
            data, sr = sf.read(audio_path)
            return len(data) / sr
        except Exception:
            return 0.0

    def cleanup_temp(self):
        """一時ファイルをクリーンアップ"""
        if os.path.exists(self.temp_dir):
            for f in os.listdir(self.temp_dir):
                if f.startswith("proc_"):
                    try:
                        os.remove(os.path.join(self.temp_dir, f))
                    except Exception:
                        pass
