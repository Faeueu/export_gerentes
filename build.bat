@echo off
chcp 65001 >nul
title Compilando ExportGerentes.exe...
echo ==============================================
echo  Compilando ExportGerentes Standalone (.exe)
echo ==============================================
python build_exe.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro durante a compilação.
    pause
    exit /b 1
)
echo.
echo Executável disponível na pasta "dist/ExportGerentes.exe".
pause
