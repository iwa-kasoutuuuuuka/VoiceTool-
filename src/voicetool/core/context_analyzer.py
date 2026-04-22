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

    # 感情キーワード辞書（日本語のニュアンスに対応）
    KEYWORDS = {
        "happy": [
            "嬉しい", "楽しい", "最高", "やった", "大好き", "ありがとう", "わーい", "素敵",
            "感謝", "ラッキー", "幸せ", "おめでとう", "すごい", "素晴らしい", "うれしい"
        ],
        "fun": [
            "笑", "ｗ", "面白い", "ウケる", "遊び", "ワクワク", "楽しみ", "期待",
            "おもしろい", "わくわく", "ハイテンション", "祭り"
        ],
        "angry": [
            "怒", "ムカつく", "最低", "ふざけるな", "バカ", "うるさい", "嫌い", "許せない",
            "殴る", "殺意", "ちくしょう", "クソ", "邪魔", "どけ", "いい加減にしろ"
        ],
        "sad": [
            "悲しい", "辛い", "寂しい", "ごめん", "申し訳", "残念", "ひどい", "泣",
            "ショック", "疲れた", "だめだ", "ダメだ", "絶望", "孤独", "つらい", "さびしい",
            "無理", "ため息"
        ],
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
        """
        text = text.strip()
        if len(text) < 2:
            # 1文字以下の場合はニュートラル設定
            return Emotion(), 0.0, 1.0

        scores = {"happy": 0.0, "fun": 0.0, "angry": 0.0, "sad": 0.0}
        
        # 1. キーワードマッチング (重複マッチを考慮)
        for emotion, words in self.KEYWORDS.items():
            for word in words:
                matches = len(re.findall(re.escape(word), text))
                if matches > 0:
                    scores[emotion] += 0.3 * matches
        
        # 2. 記号解析 (感嘆符の数による増幅)
        exclamation_matches = self.patterns["strong_exclamation"].findall(text)
        if exclamation_matches:
            # 強い強調
            scores["angry"] += 0.6
            scores["happy"] += 0.3
        else:
            exclamation_matches = self.patterns["exclamation"].findall(text)
            if exclamation_matches:
                # 通常の強調
                scores["happy"] += 0.2
                scores["angry"] += 0.2
            
        if self.patterns["question"].search(text):
            scores["fun"] += 0.15
            
        if self.patterns["pause"].search(text):
            # 文中の「...」は悲しみや含みのニュアンス
            scores["sad"] += 0.35
            
        # 3. 文末表現と助詞の解析
        if text.endswith(("！", "!")):
            # 勢いのある文末
            if any(text.endswith(w) for w in ["だ", "ぞ", "ぜ", "ろ"]):
                scores["angry"] += 0.3
            if any(text.endswith(w) for w in ["よ", "ね", "わ"]):
                scores["happy"] += 0.2

        if text.endswith(("？", "?")):
            # 疑問文
            if any(text.endswith(w) for w in ["か", "の"]):
                scores["fun"] += 0.1

        # 特定の助動詞
        if "なきゃ" in text or "なれば" in text:
            scores["sad"] += 0.1  # 義務感や不安
        if "だよ" in text or "だね" in text:
            scores["happy"] += 0.1  # 親しみ

        # 4. Emotionオブジェクトの作成 (0.0 ～ 1.0 にクランプ)
        emotion = Emotion(
            happy=max(0.0, min(1.0, scores["happy"])),
            fun=max(0.0, min(1.0, scores["fun"])),
            angry=max(0.0, min(1.0, scores["angry"])),
            sad=max(0.0, min(1.0, scores["sad"]))
        )

        # 5. 推奨パラメータの計算 (感情の組み合わせによる動的な調整)
        # 基本値
        base_pitch = 0.0
        base_speed = 1.0

        # ピッチ変化 (Angry/Happyは高く、Sadは低く)
        recommended_pitch = base_pitch + (emotion.happy * 1.8) + (emotion.angry * 2.5) - (emotion.sad * 3.0)
        
        # 速度変化 (Angry/Funは速く、Sadは遅く)
        recommended_speed = base_speed + (emotion.fun * 0.25) + (emotion.angry * 0.15) - (emotion.sad * 0.15)
        
        # クランプ処理
        recommended_pitch = max(-10.0, min(10.0, recommended_pitch))
        recommended_speed = max(0.5, min(2.0, recommended_speed))

        return emotion, recommended_pitch, recommended_speed
