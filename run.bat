@echo off
chcp 65001 >nul
title VoiceTool — 音声編集ツール

echo ========================================
echo   VoiceTool — 起動中...
echo ========================================

REM スクリプトのディレクトリに移動
cd /d "%~dp0"

REM Python実行
set PYTHONPATH=%~dp0src;%PYTHONPATH%

if exist "python\python.exe" (
    REM ポータブルPython環境
    echo ポータブルPython環境を使用します
    python\python.exe src\voicetool\main.py
) else (
    REM システムPython
    echo システムPythonを判定中...
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        echo python コマンドを使用します
        python src\voicetool\main.py
    ) else (
        where py >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            echo py コマンドを使用します
            py -3 src\voicetool\main.py
        ) else (
            echo [ERROR] Python が見つかりません。Python をインストールするか PATH を通してください。
            pause
            exit /b 1
        )
    )
)

if errorlevel 1 (
    echo.
    echo エラーが発生しました。
    echo ログを確認してください。
    pause
)
