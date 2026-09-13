@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" exit /b 1
".venv\Scripts\pythonw.exe" watcher.py
