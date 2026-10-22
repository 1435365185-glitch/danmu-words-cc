@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py "%~dp0word_manager.py"
) else (
    python "%~dp0word_manager.py"
)
