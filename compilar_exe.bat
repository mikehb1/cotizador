@echo off
REM Compila el Cotizador en un .exe independiente de Windows.
REM Requiere Python 3 + PyInstaller (pip install pyinstaller).
cd /d "%~dp0"

echo.
echo [1/3] Instalando PyInstaller (si no esta)...
python -m pip install pyinstaller --quiet

echo [2/3] Compilando Cotizador.exe...
python -m PyInstaller --noconfirm --onefile --name "Cotizador" ^
  --add-data "index.html;." ^
  --add-data "logo.png;." ^
  server.py

echo [3/3] Listo.
echo.
echo El ejecutable esta en:  dist\Cotizador.exe
echo.
echo NOTA: Si Windows bloquea el .exe (Smart App Control / antivirus),
echo       ve a Propiedades y marca "Desbloquear", o copialo a otra PC
echo       sin esa politica. El .exe NO esta firmado digitalmente.
pause
