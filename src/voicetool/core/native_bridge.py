# -*- coding: utf-8 -*-
import os
import ctypes
import numpy as np
from typing import Optional, Tuple

class NativeBridge:
    """C/Assembly 高速化エンジンへのブリッジ"""
    
    _lib = None
    _failed = False

    @classmethod
    def _load_lib(cls):
        if cls._lib is not None or cls._failed:
            return
            
        base_path = os.path.dirname(__file__)
        dll_name = "fast_waveform.dll"
        dll_path = os.path.join(base_path, dll_name)
        
        if not os.path.exists(dll_path):
            cls._failed = True
            return

        try:
            cls._lib = ctypes.CDLL(dll_path)
            # void get_envelope(const float* data, size_t total_samples, int width, float* out_min, float* out_max)
            cls._lib.get_envelope.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float)
            ]
            cls._lib.get_envelope.restype = None
        except Exception as e:
            print(f"Native engine load failed: {e}")
            cls._failed = True

    @classmethod
    def is_available(cls) -> bool:
        cls._load_lib()
        return cls._lib is not None

    @classmethod
    def get_envelope(cls, data: np.ndarray, width: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        ネイティブエンジンを使用してエンベロープを抽出。
        
        Args:
            data: 入力音声 (float32 numpy array)
            width: ターゲット幅 (pixel)
            
        Returns:
            (min_array, max_array) のタプル。失敗時は None。
        """
        if not cls.is_available():
            return None
            
        if data.size == 0:
            return np.zeros(width, dtype=np.float32), np.zeros(width, dtype=np.float32)

        if data.dtype != np.float32:
            data = data.astype(np.float32)
        
        # メモリの連続性を保証
        data = np.ascontiguousarray(data)
            
        out_min = np.zeros(width, dtype=np.float32)
        out_max = np.zeros(width, dtype=np.float32)
        
        try:
            cls._lib.get_envelope(
                data.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                data.size,
                width,
                out_min.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                out_max.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            )
            return out_min, out_max
        except Exception as e:
            print(f"Native execution failed: {e}")
            return None
