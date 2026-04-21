# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
import soundfile as sf

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.getcwd(), "src"))

from voicetool.core.engine_factory import EngineFactory
from voicetool.core.engine_base import BaseTTSEngine

def test_abstraction():
    print("=== Testing Engine Abstraction ===")
    
    models_dir = "test_models"
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"Available engines: {EngineFactory.get_engine_ids()}")
    
    # 1. Mockエンジンのテスト
    print("\n--- Testing MockEngine ---")
    engine = EngineFactory.create_engine("mock", models_dir)
    assert isinstance(engine, BaseTTSEngine)
    
    engine.load_model(lambda m: print(f"  [Progress] {m}"))
    assert engine.is_ready()
    
    out_path = "test_mock_output.wav"
    res_path = engine.synthesize("Hello abstraction", "dummy.wav", output_path=out_path)
    
    assert os.path.exists(res_path)
    data, sr = sf.read(res_path)
    print(f"  Generated audio: {len(data)} samples at {sr}Hz")
    assert sr == engine.get_sample_rate()
    
    engine.unload()
    assert not engine.is_ready()
    
    if os.path.exists(out_path): os.remove(out_path)
    print("MockEngine test: PASSED")

    # 2. XTTS v2 インスタンス化テスト（ロードはしない）
    print("\n--- Testing XTTSv2Engine Instantiation ---")
    xtts = EngineFactory.create_engine("xtts_v2", models_dir)
    assert isinstance(xtts, BaseTTSEngine)
    print("XTTSv2Engine instantiation: PASSED")

if __name__ == "__main__":
    try:
        test_abstraction()
        print("\n=== All Abstraction Tests: PASSED ===")
    except Exception as e:
        print(f"\n!!! Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
