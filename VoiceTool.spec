# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import importlib.util
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

def get_pkg_path(pkg_name):
    """パッケージのインストールパスを取得する"""
    spec = importlib.util.find_spec(pkg_name)
    if spec and spec.origin:
        return os.path.dirname(spec.origin)
    return None

# パッケージパスの取得
tts_path = get_pkg_path('TTS')
trainer_path = get_pkg_path('trainer')
coqpit_path = get_pkg_path('coqpit')

print(f"--- Spec Build Config ---")
print(f"TTS Path: {tts_path}")
print(f"Trainer Path: {trainer_path}")
print(f"Coqpit Path: {coqpit_path}")

# データファイルの収集
# 標準のデータ収集（json, version等）
tts_datas = collect_data_files('TTS')
trainer_datas = collect_data_files('trainer')

# 追加の物理同梱データ
# パッケージ全体を物理的にコピーすることで TorchScript のソースアクセスエラーを回避する
extra_datas = [
    ('bin', 'bin'),
    ('src/voicetool', 'voicetool'),
]

if tts_path:
    extra_datas.append((tts_path, 'TTS'))
if trainer_path:
    extra_datas.append((trainer_path, 'trainer'))
if coqpit_path:
    extra_datas.append((coqpit_path, 'coqpit'))

a = Analysis(
    ['src/launcher.py'],
    pathex=['src', '.'],
    binaries=[
        ('src/voicetool/core/fast_waveform.dll', 'voicetool/core'),
        ('src/voicetool/core/native_dsp.dll', 'voicetool/core'),
        ('bin/sndfile.dll', '.'),
    ],
    datas=extra_datas + tts_datas + trainer_datas,
    hiddenimports=[
        'sounddevice',
        'soundfile',
        'torch',
        'PyQt6',
        'numpy',
        'pydub',
        'onnxruntime',
        'faster_whisper',
        'voicetool.ui.main_window',
        'voicetool.core.context_analyzer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 以下のパッケージをコンパイル対象(PYZ)から除外し、物理同梱を優先させる
    excludes=['TTS', 'trainer', 'coqpit'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VoiceTool',
)
