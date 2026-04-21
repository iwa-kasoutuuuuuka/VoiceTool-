# -*- coding: utf-8 -*-
import os
import ctypes
import numpy as np
from typing import Optional

class NativeDSPBridge:
    """ネイティブ D.S.P. エンジンへのブリッジ"""
    
    _lib = None
    _failed = False

    @classmethod
    def _load_lib(cls):
        if cls._lib is not None or cls._failed:
            return
            
        base_path = os.path.dirname(__file__)
        dll_name = "native_dsp.dll"
        dll_path = os.path.join(base_path, dll_name)
        
        if not os.path.exists(dll_path):
            cls._failed = True
            return

        try:
            cls._lib = ctypes.CDLL(dll_path)
            
            # apply_gain(float* data, size_t n, float gain_raw)
            cls._lib.apply_gain.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_float
            ]
            cls._lib.apply_gain.restype = None

            # apply_clipping(float* data, size_t n, float threshold)
            cls._lib.apply_clipping.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_float
            ]
            cls._lib.apply_clipping.restype = None

            # copy_buffer(float* dst, const float* src, size_t n)
            cls._lib.copy_buffer.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t
            ]
            cls._lib.copy_buffer.restype = None

            # fill_silence(float* dst, size_t n)
            cls._lib.fill_silence.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t
            ]
            cls._lib.fill_silence.restype = None

        except Exception as e:
            print(f"Native DSP engine load failed: {e}")
            cls._failed = True

    @classmethod
    def is_available(cls) -> bool:
        cls._load_lib()
        return cls._lib is not None

    @classmethod
    def apply_gain(cls, data: np.ndarray, gain_db: float):
        """音量調整をネイティブ実行 (修正: dBをリニア倍率に変換)"""
        if not cls.is_available(): return False
        if abs(gain_db) < 0.01: return True
        
        gain_raw = 10.0 ** (gain_db / 20.0)
        
        # NumPy配列をfloat32に強制し、連続メモリであることを確認
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        
        # メモリの連続性を保証
        data = np.ascontiguousarray(data)
            
        try:
            cls._lib.apply_gain(
                data.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                data.size,
                ctypes.c_float(gain_raw)
            )
            return True
        except Exception as e:
            print(f"Native apply_gain failed: {e}")
            return False

    @classmethod
    def concatenate(cls, buffers: list, silence_samples_list: list) -> Optional[np.ndarray]:
        """
        複数のバッファを無音を挟んで高速連結。
        
        Args:
            buffers: np.ndarray のリスト
            silence_samples_list: 各バッファの後に挿入する無音サンプル数のリスト
        """
        if not cls.is_available(): return None
        
        if not buffers: return None
        
        # すべてを float32 かつ連続メモリに変換
        prepared_buffers = []
        for b in buffers:
            if b.size == 0: continue
            b_f32 = b.astype(np.float32) if b.dtype != np.float32 else b
            prepared_buffers.append(np.ascontiguousarray(b_f32))
        
        if not prepared_buffers: return None

        total_samples = sum(len(b) for b in prepared_buffers) + sum(silence_samples_list)
        if total_samples == 0: return None
        
        # チャンネル数は最初のバッファに合わせる
        channels = buffers[0].shape[1] if buffers[0].ndim > 1 else 1
        
        if channels > 1:
            out_shape = (total_samples, channels)
            total_elements = total_samples * channels
        else:
            out_shape = (total_samples,)
            total_elements = total_samples

        result = np.zeros(out_shape, dtype=np.float32)
        
        try:
            curr_pos = 0
            for i, buf in enumerate(prepared_buffers):
                # バッファをコピー
                n_elements = buf.size
                cls._lib.copy_buffer(
                    result.ctypes.data_as(ctypes.POINTER(ctypes.c_float))[curr_pos:],
                    buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    n_elements
                )
                curr_pos += n_elements
                
                # 無音を挿入
                if i < len(silence_samples_list):
                    s_elements = silence_samples_list[i] * channels
                    if s_elements > 0:
                        cls._lib.fill_silence(
                            result.ctypes.data_as(ctypes.POINTER(ctypes.c_float))[curr_pos:],
                            s_elements
                        )
                        curr_pos += s_elements
            return result
        except Exception as e:
            print(f"Native concatenate failed: {e}")
            return None
