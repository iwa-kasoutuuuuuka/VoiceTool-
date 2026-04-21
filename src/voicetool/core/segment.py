# -*- coding: utf-8 -*-
"""
セグメントデータクラス
音声合成の最小単位。テキスト・パラメータ・感情情報を保持する。
"""
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Emotion:
    """感情パラメータ（各値 0.0 ～ 1.0）"""
    happy: float = 0.0   # 幸せ
    fun: float = 0.0     # 楽しみ
    angry: float = 0.0   # 怒り
    sad: float = 0.0     # 悲しみ

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Emotion":
        return cls(
            happy=d.get("happy", 0.0),
            fun=d.get("fun", 0.0),
            angry=d.get("angry", 0.0),
            sad=d.get("sad", 0.0),
        )


@dataclass
class Segment:
    """
    音声セグメント
    テキスト1行ごとに1セグメントが対応する。
    """
    text: str = ""
    start: float = 0.0          # タイムライン上の開始位置（秒）
    end: float = 0.0            # タイムライン上の終了位置（秒）
    speed: float = 1.0          # 速さ（0.5 ～ 2.0）
    pitch: float = 0.0          # ピッチ（-12 ～ +12 半音）
    volume: float = 0.0         # 音量（-20 ～ +20 dB）
    length: float = 1.0         # 長さ係数（0.5 ～ 2.0）
    pause_after: float = 0.5    # セグメント後のポーズ（秒）
    emotion: Emotion = field(default_factory=Emotion)
    audio_path: Optional[str] = None  # 加工済み音声のキャッシュパス
    raw_audio_path: Optional[str] = None  # TTS生成直後の音声パス

    def get_effective_pitch(self) -> float:
        """感情を反映した実効ピッチ（半音）"""
        e = self.emotion
        return self.pitch + e.happy * 2 + e.angry * 1 - e.sad * 2

    def get_effective_speed(self) -> float:
        """感情を反映した実効速度"""
        e = self.emotion
        base = self.speed + e.fun * 0.3 - e.sad * 0.2
        # 0.3 ～ 3.0 にクランプ
        return max(0.3, min(3.0, base))

    def get_effective_volume(self) -> float:
        """感情を反映した実効音量（dB）"""
        e = self.emotion
        return self.volume + e.angry * 2

    def cache_key(self, ref_audio: str, language: str) -> str:
        """キャッシュキー生成（パラメータのハッシュ）"""
        params = {
            "text": self.text,
            "speed": round(self.get_effective_speed(), 4),
            "pitch": round(self.get_effective_pitch(), 4),
            "volume": round(self.get_effective_volume(), 4),
            "length": round(self.length, 4),
            "pause_after": round(self.pause_after, 4),
            "ref_audio": ref_audio,
            "language": language,
        }
        raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def duration(self) -> float:
        """セグメントの長さ（秒）"""
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        """辞書に変換（保存用）"""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        """辞書から復元"""
        d = d.copy()
        emotion_data = d.pop("emotion", {})
        d["emotion"] = Emotion.from_dict(emotion_data)
        return cls(**d)
