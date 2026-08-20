"""
Ponto de entrada principal do Export Gerentes.
"""

import sys
from pathlib import Path

# Garante que a pasta src está no sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# pyrefly: ignore [missing-import]
from export_gerentes.ui.main_window import PayrollApp


def main() -> None:
    app = PayrollApp()
    app.mainloop()


if __name__ == "__main__":
    main()
