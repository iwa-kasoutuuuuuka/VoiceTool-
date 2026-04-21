# -*- coding: utf-8 -*-
"""
文脈解析エンジン。
テキストから感情を推論し、パラメータを自動設定する。
"""
import re
from typing import Tuple
from voicetool.core.segment import Emotion

class ContextAnalyzer:
    """日本語文脈・感情解析器"""

    # 感情キーワード辞書
    KEYWORDS = {
        "happy": ["嬉しい", "楽しい", "最高", "やった", "大好き", "ありがとう", "わーい", "素敵"],
        "fun": ["笑", "ｗ", "面白い", "ウケる", "遊び", "ワクワク", "楽しみ"],
        "angry": ["怒", "ムカつく", "最低", "ふざけるな", "バカ", "うるさい", "嫌い", "許せない", "っ！"],
        "sad": ["悲しい", "辛い", "寂しい", "ごめん", "申し訳", "残念", "…", "ひどい", "泣"],
    }

    def __init__(self):
        # コンパイル済みの正規表現
        self.patterns = {
            "question": re.compile(r"[？\?]"),
            "exclamation": re.compile(r"[！\!]"),
            "strong_exclamation": re.compile(r"[！\!]{2,}"),
            "pause": re.compile(r"[\.\.\.…]"),
        }

    def analyze(self, text: str) -> Tuple[Emotion, float, float]:
        """
        テキストを解析して感情とパラメータ（ピッチ、速度）を返す。
        Returns:
            (Emotion, recommended_pitch, recommended_speed)
        """
        if not text:
            return Emotion(), 0.0, 1.0

        scores = {"happy": 0.0, "fun": 0.0, "angry": 0.0, "sad": 0.0}
        
        # 1. キーワードマッチング
        for emotion, words in self.KEYWORDS.items():
            for word in words:
                if word in text:
                    scores[emotion] += 0.4
        
        # 2. 記号解析
        if self.patterns["strong_exclamation"].search(text):
            scores["angry"] += 0.5
            scores["fun"] += 0.2
        elif self.patterns["exclamation"].search(text):
            scores["happy"] += 0.2
            scores["angry"] += 0.1
            
        if self.patterns["question"].search(text):
            scores["fun"] += 0.1
            
        if self.patterns["pause"].search(text):
            scores["sad"] += 0.4
            
        # 3. 文末表現（簡易）
        if text.endswith(("だ！", "ぞ！", "よ！")):
            scores["angry"] += 0.2
        if text.endswith(("ね", "かな", "そう")):
            scores["happy"] += 0.1

        # 4. Emotionオブジェクトの作成 (0.0 ～ 1.0 にクランプ)
        emotion = Emotion(
            happy=min(1.0, scores["happy"]),
            fun=min(1.0, scores["fun"]),
            angry=min(1.0, scores["angry"]),
            sad=min(1.0, scores["sad"])
        )

        # 5. 推奨パラメータの計算
        # 怒りはピッチ上げ、悲しみは下げ、楽しさは速度上げ
        recommended_pitch = (emotion.happy * 1.5) + (emotion.angry * 2.0) - (emotion.sad * 2.5)
        recommended_speed = 1.0 + (emotion.fun * 0.2) + (emotion.angry * 0.1) - (emotion.sad * 0.1)
        
        return emotion, recommended_pitch, recommended_speed
