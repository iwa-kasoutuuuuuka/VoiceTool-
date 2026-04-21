# -*- coding: utf-8 -*-
"""
プロジェクト管理。
.vprojファイル（JSON形式）の保存・読込を行う。
"""
import json
import os
from typing import List, Optional

from voicetool.core.segment import Segment


class Project:
    """プロジェクト管理クラス"""

    VERSION = "1.0"

    def __init__(self):
        self.segments: List[Segment] = []
        self.reference_audio: str = ""       # リファレンス音声パス
        self.language: str = "ja"            # 言語（ja / en）
        self.file_path: Optional[str] = None # 保存先パス
        self.modified: bool = False          # 変更フラグ

    @property
    def name(self) -> str:
        """プロジェクト名"""
        if self.file_path:
            return os.path.splitext(os.path.basename(self.file_path))[0]
        return "無題のプロジェクト"

    def new(self):
        """新規プロジェクト"""
        self.segments = []
        self.reference_audio = ""
        self.language = "ja"
        self.file_path = None
        self.modified = False

    def add_segment(self, segment: Segment):
        """セグメント追加"""
        self.segments.append(segment)
        self.modified = True

    def remove_segment(self, index: int):
        """セグメント削除"""
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
            self.modified = True

    def update_segments_from_text(self, text: str):
        """
        テキストからセグメントリストを更新。
        改行ごとに1セグメント。既存セグメントのパラメータは維持する。
        """
        lines = [line for line in text.split("\n") if line.strip()]
        new_segments = []   

        for i, line in enumerate(lines):
            if i < len(self.segments):
                # 既存セグメントのテキストを更新
                seg = self.segments[i]
                if seg.text != line.strip():
                    seg.text = line.strip()
                    seg.audio_path = None  # テキスト変更によりキャッシュ無効
                    seg.raw_audio_path = None
                new_segments.append(seg)
            else:
                # 新規セグメント
                new_segments.append(Segment(text=line.strip()))

        self.segments = new_segments
        self.modified = True

    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "version": self.VERSION,
            "reference_audio": self.reference_audio,
            "language": self.language,
            "segments": [seg.to_dict() for seg in self.segments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        """辞書から復元"""
        proj = cls()
        proj.language = d.get("language", "ja")
        proj.reference_audio = d.get("reference_audio", "")
        proj.segments = [
            Segment.from_dict(s) for s in d.get("segments", [])
        ]
        return proj

    def save(self, path: Optional[str] = None) -> str:
        """
        プロジェクトを.vprojファイルに保存。
        """
        save_path = path or self.file_path
        if not save_path:
            raise ValueError("保存先パスが指定されていません")

        if not save_path.endswith(".vproj"):
            save_path += ".vproj"

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

        self.file_path = save_path
        self.modified = False
        return save_path

    @classmethod
    def load(cls, path: str) -> "Project":
        """
        .vprojファイルからプロジェクトを読込。
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        proj = cls.from_dict(data)
        proj.file_path = path
        proj.modified = False
        return proj

    def get_total_duration(self) -> float:
        """全セグメントの合計時間（秒）"""
        if not self.segments:
            return 0.0
        return max(seg.end for seg in self.segments) if self.segments else 0.0

    def recalculate_timings(self):
        """セグメントのタイミングを再計算"""
        current_time = 0.0
        for seg in self.segments:
            seg.start = current_time
            if seg.duration > 0:
                seg.end = seg.start + seg.duration
            else:
                # 音声未生成の場合、テキスト長から概算
                estimated = max(0.5, len(seg.text) * 0.15)
                seg.end = seg.start + estimated
            current_time = seg.end + seg.pause_after
