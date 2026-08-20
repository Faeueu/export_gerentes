"""
Script para compilar o executável standalone do Export Gerentes via PyInstaller.
Gera um arquivo único .exe sem terminal/console e com os dados embutidos.
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"


def build() -> None:
    print("Iniciando compilação com PyInstaller...")

    colaboradores_csv = ROOT_DIR / "colaboradores.csv"
    eventos_csv = ROOT_DIR / "eventos.csv"

    add_data_sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name",
        "ExportGerentes",
        "--paths",
        str(SRC_DIR),
        f"--add-data={colaboradores_csv}{add_data_sep}.",
        f"--add-data={eventos_csv}{add_data_sep}.",
        "--clean",
        str(ROOT_DIR / "main.py"),
    ]

    print(f"Executando comando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode == 0:
        exe_path = DIST_DIR / ("ExportGerentes.exe" if sys.platform == "win32" else "ExportGerentes")
        print("\n==========================================")
        print("Build concluído com sucesso!")
        print(f"Executável gerado em: {exe_path}")
        print("==========================================")
    else:
        print("\nFalha na compilação do executável.", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
