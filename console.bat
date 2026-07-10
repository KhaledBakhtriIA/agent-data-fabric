@echo off
REM ============================================================
REM  QA Reliability Intelligence - console launcher (Windows)
REM  Double-click this file (or run it) to open the interactive
REM  console in its own terminal window. No VS Code needed.
REM ============================================================
cd /d "%~dp0"
python -m reliability
echo.
echo (console closed - press any key to exit)
pause >nul
