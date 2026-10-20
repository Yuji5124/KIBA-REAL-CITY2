@echo off
rem KIBA PARK REBUILD - Phase 1 data fetch (v2). Writes only to this project's data\raw.
rem Does not install packages. Re-run safely: finished files are reused.
cd /d "%~dp0\..\.."
if not exist "CLAUDE.md" (echo This is not the KIBA PARK REBUILD folder. & pause & exit /b 1)
set PY=py -3
if exist "%USERPROFILE%\venv312\Scripts\python.exe" set PY="%USERPROFILE%\venv312\Scripts\python.exe"
%PY% -c "import pyproj, PIL" 2>nul
if errorlevel 1 (echo pyproj / Pillow not found. Install with:  %PY% -m pip install pyproj pillow & pause & exit /b 1)
%PY% scripts\fetch\fetch_phase1_data.py %*
if errorlevel 1 (echo Some downloads failed. Run this file again later. & pause & exit /b 1)
%PY% scripts\fetch\verify_phase1_data.py
pause
