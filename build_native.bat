@echo off
setlocal
echo === VoiceTool Native Engine Builder ===

set SRC=src\voicetool\core\fast_waveform.c
set DLL=src\voicetool\core\fast_waveform.dll

:: Check for GCC (MinGW)
where gcc >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [GCC] Compiling with GCC...
    gcc -O3 -shared -o "%DLL%" "%SRC%" -mavx2
    if %ERRORLEVEL% equ 0 goto success
)

:: Check for CL (MSVC)
where cl >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [MSVC] Compiling with MSVC...
    cl /O2 /LD /Fe:"%DLL%" "%SRC%"
    if %ERRORLEVEL% equ 0 goto success
)

echo [ERROR] No compatible compiler (gcc or cl) found in PATH.
echo Please install MinGW-w64 or Visual Studio Build Tools.
pause
exit /b 1

:success
echo [SUCCESS] Native engine built: %DLL%
exit /b 0
