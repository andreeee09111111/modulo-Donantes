@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero crea el entorno .venv e instala requirements-dev.txt. Consulta README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" iniciar.py
pause
