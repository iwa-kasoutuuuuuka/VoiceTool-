# -*- coding: utf-8 -*-
import os
from typing import Dict, Type
from voicetool.core.engine_base import BaseTTSEngine
from voicetool.core.engines.xtts_engine import XTTSv2Engine
from voicetool.core.engines.mock_engine import MockEngine

class EngineFactory:
    """音声合成エンジンの生成を管理するファクトリ"""
    
    _registry: Dict[str, Type[BaseTTSEngine]] = {
        "xtts_v2": XTTSv2Engine,
        "mock": MockEngine
    }

    @classmethod
    def get_engine_ids(cls):
        """利用可能なエンジンIDのリストを返す"""
        return list(cls._registry.keys())

    @classmethod
    def create_engine(cls, engine_id: str, models_dir: str) -> BaseTTSEngine:
        """指定されたIDのエンジンインスタンスを生成"""
        if engine_id not in cls._registry:
            raise ValueError(f"未知のエンジンID: {engine_id}")
        
        engine_class = cls._registry[engine_id]
        return engine_class(models_dir)

    @classmethod
    def register_engine(cls, engine_id: str, engine_class: Type[BaseTTSEngine]):
        """新しいエンジンを登録（プラグイン用）"""
        cls._registry[engine_id] = engine_class
