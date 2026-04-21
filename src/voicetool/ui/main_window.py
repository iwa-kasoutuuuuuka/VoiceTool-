# -*- coding: utf-8 -*-
"""
メインウィンドウ
全UIパネルの統合とアプリケーションロジックの制御。
"""
import os
import sys
import logging
import traceback
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QApplication, QStatusBar, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

from voicetool.ui.styles import get_stylesheet, COLORS
from voicetool.ui.toolbar import ToolBar
from voicetool.ui.text_panel import TextPanel
from voicetool.ui.timeline_panel import TimelinePanel
from voicetool.ui.parameter_panel import ParameterPanel
from voicetool.ui.log_panel import LogPanel
from voicetool.core.project import Project
from voicetool.core.segment import Segment
from voicetool.core.engine_base import BaseTTSEngine
from voicetool.core.engine_factory import EngineFactory
from voicetool.core.audio_processor import AudioProcessor
from voicetool.core.cache_manager import CacheManager
from voicetool.core.context_analyzer import ContextAnalyzer
from voicetool.core.player import AudioPlayer

logger = logging.getLogger(__name__)


class GenerateWorker(QThread):
    """音声生成ワーカースレッド"""

    segment_started = pyqtSignal(int, str)    # (index, status)
    segment_finished = pyqtSignal(int, str)   # (index, audio_path)
    segment_error = pyqtSignal(int, str)      # (index, error)
    waveform_ready = pyqtSignal(int, object)  # (index, numpy_array)
    partial_waveform_ready = pyqtSignal(int, object) # 生成中のチャンク
    all_finished = pyqtSignal()

    def __init__(
        self,
        project: Project,
        tts_engine: BaseTTSEngine,
        audio_processor: AudioProcessor,
        cache_manager: CacheManager,
        app_dir: str,
    ):
        super().__init__()
        self.project = project
        self.tts = tts_engine
        self.processor = audio_processor
        self.cache = cache_manager
        self.app_dir = app_dir

    def run(self):
        import soundfile as sf

        ref_audio = self.project.reference_audio
        language = self.project.language

        # リファレンス音声をWAVに変換（MP3対応）
        if ref_audio and ref_audio.lower().endswith(".mp3"):
            try:
                ref_audio = self.processor.convert_to_wav(ref_audio)
            except Exception as e:
                logger.error(f"リファレンス音声の変換に失敗: {e}")

        for i, seg in enumerate(self.project.segments):
            if not seg.text.strip():
                continue

            self.segment_started.emit(i, f"セグメント {i+1} を処理中...")

            try:
                # キャッシュチェック
                cache_key = seg.cache_key(ref_audio, language)
                cached = self.cache.get(cache_key)

                if cached:
                    seg.audio_path = cached
                    logger.info(f"セグメント {i+1}: キャッシュ使用")
                else:
                    # TTS 生成（ストリーミング）
                    all_chunks = []
                    for chunk in self.tts.synthesize_stream(
                        text=seg.text,
                        speaker_wav=ref_audio,
                        language=language,
                    ):
                        all_chunks.append(chunk)
                        # 生成中のデータを一部送信（インクリメンタル描画用）
                        self.partial_waveform_ready.emit(i, chunk)

                    if not all_chunks:
                        raise RuntimeError("音声の生成に失敗しました")

                    # 結合してファイル保存（加工前）
                    raw_audio = np.concatenate(all_chunks)
                    raw_path = self.processor._get_temp_path()
                    sf.write(raw_path, raw_audio, self.tts.get_sample_rate())
                    seg.raw_audio_path = raw_path

                    # 音声加工（ピッチカーブ適用）
                    processed_path = self.processor.process_segment(
                        input_path=raw_path,
                        pitch_semitones=seg.get_effective_pitch(),
                        speed_factor=seg.get_effective_speed(),
                        volume_db=seg.get_effective_volume(),
                        pause_after=seg.pause_after,
                        pitch_curve=seg.pitch_curve,
                    )

                    # キャッシュに保存
                    cached_path = self.cache.put(cache_key, processed_path)
                    seg.audio_path = cached_path

                # 最終的な波形データを読み込み
                if seg.audio_path and os.path.exists(seg.audio_path):
                    data, sr = sf.read(seg.audio_path)
                    seg.end = seg.start + len(data) / sr
                    self.waveform_ready.emit(i, data)

                self.segment_finished.emit(i, seg.audio_path or "")

            except Exception as e:
                logger.error(f"セグメント {i+1} エラー: {e}")
                logger.error(traceback.format_exc())
                self.segment_error.emit(i, str(e))

        # タイミング再計算
        self.project.recalculate_timings()
        self.all_finished.emit()


class MainWindow(QMainWindow):
    """メインウィンドウ"""

        self.app_dir = app_dir
        self.project = Project()
        
        # エンジンファクトリからエンジンを生成（デフォルト: xtts_v2）
        self.tts_engine = EngineFactory.create_engine(
            "xtts_v2", 
            os.path.join(app_dir, "models")
        )
        
        self.audio_processor = AudioProcessor(
            os.path.join(app_dir, "bin"),
            os.path.join(app_dir, "temp"),
        )
        self.cache_manager = CacheManager(os.path.join(app_dir, "temp", "cache"))
        self.context_analyzer = ContextAnalyzer()
        self.player = AudioPlayer()
        self._selected_segment: int = -1
        self._generate_worker: Optional[GenerateWorker] = None
        self._cursor_timer = QTimer()
        self._cursor_timer.setInterval(50)  # 50ms間隔で更新
        self._cursor_timer.timeout.connect(self._update_cursor)

        self._setup_ui()
        self._connect_signals()
        self._update_title()

        logger.info("アプリケーション起動完了")

    def _setup_ui(self):
        """UIを構築"""
        self.setWindowTitle("VoiceTool — 音声編集ツール")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 850)

        # スタイルシート適用
        self.setStyleSheet(get_stylesheet())

        # ツールバー
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)

        # 中央ウィジェット
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 上下スプリッター（メイン領域 / ログ）
        v_splitter = QSplitter(Qt.Orientation.Vertical)

        # 左右3ペインスプリッター
        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左パネル: テキスト
        self.text_panel = TextPanel()
        h_splitter.addWidget(self.text_panel)

        # 中央パネル: タイムライン
        self.timeline_panel = TimelinePanel()
        h_splitter.addWidget(self.timeline_panel)

        # 右パネル: パラメータ
        self.parameter_panel = ParameterPanel()
        h_splitter.addWidget(self.parameter_panel)

        # スプリッター比率
        h_splitter.setStretchFactor(0, 2)  # テキスト
        h_splitter.setStretchFactor(1, 4)  # タイムライン
        h_splitter.setStretchFactor(2, 2)  # パラメータ
        h_splitter.setSizes([280, 560, 280])

        v_splitter.addWidget(h_splitter)

        # ログパネル
        self.log_panel = LogPanel()
        v_splitter.addWidget(self.log_panel)

        v_splitter.setStretchFactor(0, 5)
        v_splitter.setStretchFactor(1, 1)
        v_splitter.setSizes([600, 150])

        main_layout.addWidget(v_splitter)
        self.setCentralWidget(central)

        # ステータスバー
        self.statusBar().showMessage("準備完了")
        self.device_label = QLabel("デバイス: 未検出")
        self.device_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding-right: 8px;")
        self.statusBar().addPermanentWidget(self.device_label)

    def _connect_signals(self):
        """シグナルを接続"""
        # ツールバー
        self.toolbar.new_project.connect(self._new_project)
        self.toolbar.open_project.connect(self._open_project)
        self.toolbar.save_project.connect(self._save_project)
        self.toolbar.play_clicked.connect(self._toggle_play)
        self.toolbar.stop_clicked.connect(self._stop)
        self.toolbar.generate_clicked.connect(self._generate_all)
        self.toolbar.export_clicked.connect(self._export)
        self.toolbar.reference_changed.connect(self._on_reference_changed)

        # テキストパネル
        self.text_panel.text_changed.connect(self._on_text_changed)
        self.text_panel.segment_selected.connect(self._select_segment)
        self.text_panel.language_changed.connect(self._on_language_changed)
        self.text_panel.auto_analyze_requested.connect(self._on_auto_analyze_requested)

        # タイムラインパネル
        self.timeline_panel.segment_selected.connect(self._select_segment)

        # パラメータパネル
        self.parameter_panel.parameter_changed.connect(self._on_parameter_changed)

        # プレーヤーコールバック
        self.player.set_callbacks(
            on_playback_finished=self._on_playback_finished,
        )

    def _update_title(self):
        """ウィンドウタイトルを更新"""
        name = self.project.name
        modified = " *" if self.project.modified else ""
        self.setWindowTitle(f"VoiceTool — {name}{modified}")

    # === ファイル操作 ===

    def _new_project(self):
        """新規プロジェクト"""
        if self.project.modified:
            ret = QMessageBox.question(
                self,
                "確認",
                "変更が保存されていません。新規プロジェクトを作成しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

        self.project.new()
        self.text_panel.set_text("")
        self.timeline_panel.set_segments([])
        self.timeline_panel.clear_waveforms()
        self.parameter_panel.clear()
        self._selected_segment = -1
        self._update_title()
        logger.info("新規プロジェクトを作成しました")

    def _open_project(self):
        """プロジェクトを開く"""
        default_dir = os.path.join(self.app_dir, "projects")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "プロジェクトを開く",
            default_dir,
            "VoiceToolプロジェクト (*.vproj)",
        )
        if not path:
            return

        try:
            self.project = Project.load(path)
            # UIを更新
            text = "\n".join(seg.text for seg in self.project.segments)
            self.text_panel.set_text(text)
            self.text_panel.set_language(self.project.language)
            if self.project.reference_audio:
                self.toolbar.set_reference_audio(self.project.reference_audio)
            self.timeline_panel.set_segments(self.project.segments)
            self.timeline_panel.clear_waveforms()
            self.parameter_panel.clear()
            self._selected_segment = -1
            self._update_title()
            logger.info(f"プロジェクトを開きました: {path}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プロジェクトを開けません:\n{e}")
            logger.error(f"プロジェクトを開けませんでした: {e}")

    def _save_project(self):
        """プロジェクトを保存"""
        if not self.project.file_path:
            default_dir = os.path.join(self.app_dir, "projects")
            os.makedirs(default_dir, exist_ok=True)
            path, _ = QFileDialog.getSaveFileName(
                self,
                "プロジェクトを保存",
                os.path.join(default_dir, "project.vproj"),
                "VoiceToolプロジェクト (*.vproj)",
            )
            if not path:
                return
        else:
            path = self.project.file_path

        try:
            self.project.save(path)
            self._update_title()
            logger.info(f"プロジェクトを保存しました: {path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗:\n{e}")

    # === テキスト・セグメント ===

    def _on_text_changed(self, text: str):
        """テキスト変更時"""
        self.project.update_segments_from_text(text)
        self.timeline_panel.set_segments(self.project.segments)
        self._update_title()

    def _select_segment(self, index: int):
        """セグメントを選択"""
        if 0 <= index < len(self.project.segments):
            self._selected_segment = index
            seg = self.project.segments[index]
            self.parameter_panel.load_segment(seg, index)
            self.timeline_panel.set_selected(index)
            self.text_panel.highlight_segment(index)
            self.statusBar().showMessage(
                f"セグメント {index + 1} / {len(self.project.segments)}"
            )

    def _on_parameter_changed(self):
        """パラメータ変更時"""
        if 0 <= self._selected_segment < len(self.project.segments):
            seg = self.project.segments[self._selected_segment]
            self.parameter_panel.save_to_segment(seg)
            self.project.modified = True
            self._update_title()

    def _on_language_changed(self, lang: str):
        """言語変更時"""
        self.project.language = lang
        self.project.modified = True
        self._update_title()

    def _on_reference_changed(self, path: str):
        """リファレンス音声変更時"""
        self.project.reference_audio = path
        self.project.modified = True
        self._update_title()
        logger.info(f"リファレンス音声を設定: {path}")

    # === 音声生成 ===

    def _generate_all(self):
        """全セグメントの音声を生成"""
        if not self.project.segments:
            QMessageBox.warning(self, "警告", "テキストを入力してください")
            return

        if not self.project.reference_audio:
            QMessageBox.warning(self, "警告", "リファレンス音声を設定してください")
            return

        if not self.tts_engine.is_ready():
            QMessageBox.warning(self, "警告", "TTSモデルが読み込まれていません")
            return

        if self._generate_worker and self._generate_worker.isRunning():
            logger.warning("生成中です。完了をお待ちください。")
            return

        logger.info("音声生成を開始します...")
        self.toolbar.generate_action.setEnabled(False)

        self._generate_worker = GenerateWorker(
            self.project,
            self.tts_engine,
            self.audio_processor,
            self.cache_manager,
            self.app_dir,
        )
        self._generate_worker.segment_started.connect(self._on_gen_segment_started)
        self._generate_worker.segment_finished.connect(self._on_gen_segment_finished)
        self._generate_worker.segment_error.connect(self._on_gen_segment_error)
        self._generate_worker.waveform_ready.connect(self._on_gen_waveform_ready)
        self._generate_worker.partial_waveform_ready.connect(self._on_gen_partial_waveform)
        self._generate_worker.all_finished.connect(self._on_gen_all_finished)
        self._generate_worker.start()

    def _on_gen_partial_waveform(self, index: int, chunk: np.ndarray):
        """生成中の波形データ受信"""
        self.timeline_panel.append_waveform_chunk(index, chunk)

    def _on_gen_segment_started(self, index: int, status: str):
        self.statusBar().showMessage(status)

    def _on_gen_segment_finished(self, index: int, audio_path: str):
        logger.info(f"セグメント {index + 1} の生成完了")

    def _on_auto_analyze_requested(self):
        """全セグメントのAI文脈解析を実行"""
        if not self.project.segments:
            return
            
        self.statusBar().showMessage("AI 文脈解析を実行中...")
        
        for seg in self.project.segments:
            emotion, pitch, speed = self.context_analyzer.analyze(seg.text)
            seg.emotion = emotion
            seg.pitch = pitch
            seg.speed = speed
            
        # UI更新（選択中のセグメントのパラメータを再表示）
        if 0 <= self._selected_segment < len(self.project.segments):
            self.parameter_panel.load_segment(self.project.segments[self._selected_segment], self._selected_segment)
        
        self.timeline_panel.update()
        self._update_title()
        self.statusBar().showMessage("AI 文脈解析が完了しました", 3000)
        logger.info("全セグメントの自動感情アノテーションを完了しました")

    def _on_gen_segment_error(self, index: int, error: str):
        logger.error(f"セグメント {index + 1} の生成エラー: {error}")

    def _on_gen_waveform_ready(self, index: int, data):
        """波形データ受信"""
        import numpy as np
        self.timeline_panel.set_waveform(index, np.array(data))

    def _on_gen_all_finished(self):
        """全セグメント生成完了"""
        self.toolbar.generate_action.setEnabled(True)
        self.timeline_panel.set_segments(self.project.segments)
        self.statusBar().showMessage("音声生成完了")
        logger.info("全セグメントの音声生成が完了しました")

    # === 再生 ===

    def _toggle_play(self):
        """再生/停止トグル"""
        if self.player.is_playing:
            self._stop()
        else:
            self._play()

    def _play(self):
        """再生"""
        audio_paths = [
            seg.audio_path for seg in self.project.segments
            if seg.audio_path and os.path.exists(seg.audio_path)
        ]

        if not audio_paths:
            QMessageBox.warning(self, "警告", "再生する音声がありません。先に音声を生成してください。")
            return

        self.player.load_multiple(audio_paths)
        self.player.play()
        self._cursor_timer.start()
        self.statusBar().showMessage("再生中...")
        logger.info("再生開始")

    def _stop(self):
        """停止"""
        self.player.stop()
        self._cursor_timer.stop()
        self.timeline_panel.set_cursor(-1)
        self.statusBar().showMessage("停止")

    def _on_playback_finished(self):
        """再生完了"""
        self._cursor_timer.stop()
        self.timeline_panel.set_cursor(-1)
        self.statusBar().showMessage("再生完了")

    def _update_cursor(self):
        """再生カーソルを更新"""
        if self.player.is_playing:
            pos = self.player.position_seconds
            self.timeline_panel.set_cursor(pos)

    # === 書き出し ===

    def _export(self):
        """音声を書き出し"""
        audio_paths = [
            seg.audio_path for seg in self.project.segments
            if seg.audio_path and os.path.exists(seg.audio_path)
        ]

        if not audio_paths:
            QMessageBox.warning(self, "警告", "書き出す音声がありません。先に音声を生成してください。")
            return

        path, filter_str = QFileDialog.getSaveFileName(
            self,
            "音声を書き出し",
            os.path.join(self.app_dir, "output.wav"),
            "WAVファイル (*.wav);;MP3ファイル (*.mp3)",
        )
        if not path:
            return

        try:
            fmt = "mp3" if path.lower().endswith(".mp3") else "wav"
            self.audio_processor.concatenate_segments(audio_paths, path, fmt)
            QMessageBox.information(self, "完了", f"書き出しが完了しました:\n{path}")
            logger.info(f"書き出し完了: {path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"書き出しに失敗:\n{e}")
            logger.error(f"書き出しエラー: {e}")

    # === TTSモデル読み込み ===

    def load_tts_model(self):
        """TTSモデルを読み込む（起動時に呼ばれる）"""
        try:
            def progress_cb(msg):
                self.statusBar().showMessage(msg)
                logger.info(msg)

            self.tts_engine.load_model(progress_callback=progress_cb)
            device = self.tts_engine.device
            self.device_label.setText(f"デバイス: {device.upper()}")
            if device == "cuda":
                self.device_label.setStyleSheet(f"color: {COLORS['success']}; padding-right: 8px;")
            else:
                self.device_label.setStyleSheet(f"color: {COLORS['warning']}; padding-right: 8px;")

        except Exception as e:
            logger.error(f"TTSモデルの読み込みに失敗: {e}")
            self.device_label.setText("デバイス: エラー")
            self.device_label.setStyleSheet(f"color: {COLORS['error']}; padding-right: 8px;")
            QMessageBox.warning(
                self,
                "TTSモデル読み込みエラー",
                f"TTSモデルの読み込みに失敗しました。\n"
                f"音声生成機能は使用できません。\n\n"
                f"エラー: {e}\n\n"
                f"インターネット接続を確認し、再起動してください。",
            )

    def closeEvent(self, event):
        """ウィンドウ閉じるとき"""
        if self.project.modified:
            ret = QMessageBox.question(
                self,
                "確認",
                "変更が保存されていません。終了しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        # クリーンアップ
        self.player.stop()
        self._cursor_timer.stop()
        if self._generate_worker and self._generate_worker.isRunning():
            self._generate_worker.terminate()
        self.audio_processor.cleanup_temp()
        event.accept()
