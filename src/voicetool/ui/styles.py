# -*- coding: utf-8 -*-
"""
ダークテーマスタイルシート
モダンなUI外観を定義する。
"""

# カラーパレット
COLORS = {
    "bg_primary": "#1a1a2e",        # メイン背景
    "bg_secondary": "#16213e",      # パネル背景
    "bg_tertiary": "#0f3460",       # アクティブ背景
    "bg_surface": "#1f2940",        # サーフェス/カード
    "bg_input": "#111827",          # 入力フィールド背景
    "border": "#2d3a5c",            # ボーダー
    "border_active": "#5b8def",     # アクティブボーダー
    "text_primary": "#e2e8f0",      # メインテキスト
    "text_secondary": "#94a3b8",    # サブテキスト
    "text_accent": "#7dd3fc",       # アクセントテキスト
    "accent": "#5b8def",            # アクセントカラー
    "accent_hover": "#7ba4f7",      # アクセントホバー
    "accent_pressed": "#4a7ad4",    # アクセント押下
    "success": "#34d399",           # 成功
    "warning": "#fbbf24",           # 警告
    "error": "#f87171",             # エラー
    "waveform": "#5b8def",          # 波形色
    "waveform_bg": "#111827",       # 波形背景
    "segment_active": "#5b8def33",  # アクティブセグメント
    "segment_border": "#5b8def",    # セグメントボーダー
    "cursor": "#f87171",            # 再生カーソル
    "slider_groove": "#111827",     # スライダー溝
}

# 感情別の色
EMOTION_COLORS = {
    "happy": "#f472b6",   # ピンク
    "fun": "#fbbf24",     # オレンジ/黄
    "angry": "#f87171",   # 赤
    "sad": "#60a5fa",     # 青
}

def get_stylesheet():
    """QSSを生成して返す (リッチ・プレミアムデザイン)"""
    return f"""
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
    }}
    
    QWidget {{
        background-color: transparent;
        color: {COLORS['text_primary']};
        font-family: 'Outfit', 'Yu Gothic UI', sans-serif;
    }}
    
    /* ツールバー */
    QToolBar {{
        background-color: {COLORS['bg_secondary']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 4px;
        spacing: 12px;
    }}
    
    QToolButton {{
        border-radius: 6px;
        padding: 6px;
        font-weight: bold;
    }}
    
    QToolButton:hover {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['accent']};
    }}
    
    QToolButton:pressed {{
        background-color: {COLORS['accent']};
    }}
    
    /* スプリッター */
    QSplitter::handle {{
        background-color: {COLORS['border']};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    
    /* パネルヘッダー */
    QLabel#label_section {{
        color: {COLORS['text_accent']};
        font-weight: bold;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    /* グループボックス */
    QGroupBox {{
        color: {COLORS['text_accent']};
        font-weight: bold;
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        margin-top: 1.5em;
        padding-top: 1em;
        background-color: {COLORS['bg_secondary']};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 5px 0 5px;
    }}
    
    /* フィールド */
    QLineEdit, QTextEdit {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        color: {COLORS['text_primary']};
        padding: 8px;
        selection-background-color: {COLORS['accent']};
    }}
    
    QLineEdit:focus, QTextEdit:focus {{
        border: 1px solid {COLORS['border_active']};
    }}
    
    /* スライダー */
    QSlider::groove:horizontal {{
        border: 1px solid {COLORS['border']};
        height: 4px;
        background: {COLORS['bg_input']};
        margin: 2px 0;
        border-radius: 2px;
    }}
    
    QSlider::handle:horizontal {{
        background: {COLORS['accent']};
        border: 1px solid {COLORS['accent']};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: {COLORS['accent_hover']};
    }}
    
    /* スクロールバー */
    QScrollBar:vertical {{
        border: none;
        background: {COLORS['bg_primary']};
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    
    QScrollBar::handle:vertical {{
        background: {COLORS['border']};
        min-height: 20px;
        border-radius: 5px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['text_secondary']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    /* ボタン */
    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        color: {COLORS['text_primary']};
        padding: 6px 16px;
        font-weight: 600;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['accent']};
        border: 1px solid {COLORS['accent_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS['accent_pressed']};
    }}
    
    QPushButton:disabled {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
    }}
    
    /* コンボボックス */
    QComboBox {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 4px 10px;
        min-width: 6em;
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_input']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['accent']};
    }}
    """
