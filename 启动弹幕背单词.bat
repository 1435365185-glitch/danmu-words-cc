@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py "%~dp0danmu_words.py"
) else (
    python "%~dp0danmu_words.py"
)
