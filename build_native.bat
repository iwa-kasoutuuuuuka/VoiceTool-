@echo off
setlocal
echo === VoiceTool Native Engine Builder ===

set SRC=src\voicetool\core\fast_waveform.c
set DLL=src\voicetool\core\fast_waveform.dll
set SRC_DSP=src\voicetool\core\native_dsp.c
set DLL_DSP=src\voicetool\core\native_dsp.dll

:: Check for GCC (MinGW)
where gcc >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [GCC] Compiling Fast Waveform...
    gcc -O3 -shared -o "%DLL%" "%SRC%" -mavx2
    echo [GCC] Compiling Native DSP Engine...
    gcc -O3 -shared -o "%DLL_DSP%" "%SRC_DSP%" -mavx2
    if %ERRORLEVEL% equ 0 goto success
)

:: Check for CL (MSVC)
where cl >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [MSVC] Compiling Fast Waveform...
    cl /O2 /LD /Fe:"%DLL%" "%SRC%"
    echo [MSVC] Compiling Native DSP Engine...
    cl /O2 /LD /Fe:"%DLL_DSP%" "%SRC_DSP%"
    if %ERRORLEVEL% equ 0 goto success
)

echo [ERROR] No compatible compiler (gcc or cl) found in PATH.
echo Please install MinGW-w64 or Visual Studio Build Tools.
pause
exit /b 1

:success
echo [SUCCESS] Native engine built: %DLL%
exit /b 0
