"""
Wrapper retrocompatível para execução e imports do export_gerentes.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from export_gerentes import (
    APP_TITLE,
    COMPANIES,
    DEFAULT_EVENTS,
    Employee,
    EmployeeFileError,
    EventFileError,
    Launch,
    PayrollEvent,
    build_record,
    employee_file_has_legacy_branch,
    format_cents,
    get_data_directory,
    load_employees,
    load_events,
    normalize_calculation_code,
    normalize_company,
    normalize_event_code,
    normalize_registration,
    parse_currency_to_cents,
    save_employees,
    save_events,
    write_txt,
)
from export_gerentes.ui.main_window import PayrollApp


def main() -> None:
    app = PayrollApp()
    app.mainloop()


if __name__ == "__main__":
    main()
