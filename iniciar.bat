@echo off
cd /d "%~dp0"
start "Cotizador" cmd /c "python server.py & pause"
