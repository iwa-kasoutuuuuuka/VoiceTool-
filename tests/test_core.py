# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil

# パス設定
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Root/src を sys.path に追加
SRC_DIR = os.path.join(os.path.dirname(ROOT_DIR), "src")
sys.path.insert(0, SRC_DIR)

from voicetool.core.segment import Segment, Emotion
from voicetool.core.project import Project
from voicetool.core.cache_manager import CacheManager

def test_core_logic():
    print("=== Core Logic Test ===")
    
    # 1. Segment & Emotion
    seg = Segment(text="こんにちは、検証テストです。")
    seg.speed = 1.2
    seg.emotion.happy = 0.5
    
    # パラメータ反映の確認
    p = seg.get_effective_pitch()
    s = seg.get_effective_speed()
    print(f"Segment: pitch={p}, speed={s}")
    
    # キャッシュキーの不変性・一意性
    key1 = seg.cache_key("ref.wav", "ja")
    seg.speed = 1.1
    key2 = seg.cache_key("ref.wav", "ja")
    print(f"Cache keys: Same? {key1 == key2}")
    assert key1 != key2, "Speed change should change cache key"

    # 2. Project
    proj = Project()
    text = "第一行目。\n第二行目。"
    proj.update_segments_from_text(text)
    print(f"Project segments: {len(proj.segments)}")
    assert len(proj.segments) == 2, "Text should split into 2 segments"
    
    # 保存と読込
    test_vproj = "test_project.vproj"
    proj.save(test_vproj)
    proj2 = Project.load(test_vproj)
    print(f"Loaded project: {proj2.segments[1].text}")
    assert proj2.segments[1].text == "第二行目。", "Loaded text mismatch"
    os.remove(test_vproj)

    # 3. CacheManager
    cache_dir = "test_cache"
    if os.path.exists(cache_dir): shutil.rmtree(cache_dir)
    cm = CacheManager(cache_dir)
    
    # ダミーファイルを保存
    dummy_wav = "dummy.wav"
    with open(dummy_wav, "w") as f: f.write("audio data")
    
    cached_path = cm.put("some_key", dummy_wav)
    print(f"Cached file: {cached_path}")
    
    # 取得
    retrieved = cm.get("some_key")
    print(f"Retrieved path: {retrieved}")
    assert retrieved is not None, "Cache lookup failed"
    
    os.remove(dummy_wav)
    shutil.rmtree(cache_dir)

    print("=== Core Logic Test: PASSED ===\n")

if __name__ == "__main__":
    try:
        test_core_logic()
    except Exception as e:
        print(f"Test FAILED: {e}")
        sys.exit(1)
