@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -c "import tkinter" >nul 2>nul
    if %errorlevel%==0 goto run_py
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import tkinter" >nul 2>nul
    if %errorlevel%==0 goto run_python
)

echo.
echo Python com suporte a interface grafica nao foi encontrado neste computador.
echo Instale o Python 3 para Windows com o componente Tcl/Tk e tente novamente.
echo Depois da instalacao, abra novamente este arquivo iniciar.bat.
echo.
pause
exit /b 1

:run_py
py app.py
goto finished

:run_python
python app.py

:finished
if errorlevel 1 pause
