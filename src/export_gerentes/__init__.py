"""
Pacote export_gerentes - Geração de lançamentos Modelo 35 Senior para gerentes e subgerentes.
"""

from .constants import APP_TITLE, COMPANIES
from .models import DEFAULT_EVENTS, Employee, Launch, PayrollEvent
from .generator import (
    build_record,
    format_cents,
    normalize_calculation_code,
    normalize_company,
    normalize_event_code,
    normalize_registration,
    parse_currency_to_cents,
    write_txt,
)
from .storage import (
    EmployeeFileError,
    EventFileError,
    employee_file_has_legacy_branch,
    get_data_directory,
    load_employees,
    load_events,
    save_employees,
    save_events,
)

__all__ = [
    "APP_TITLE",
    "COMPANIES",
    "DEFAULT_EVENTS",
    "Employee",
    "EmployeeFileError",
    "EventFileError",
    "Launch",
    "PayrollEvent",
    "build_record",
    "employee_file_has_legacy_branch",
    "format_cents",
    "get_data_directory",
    "load_employees",
    "load_events",
    "normalize_calculation_code",
    "normalize_company",
    "normalize_event_code",
    "normalize_registration",
    "parse_currency_to_cents",
    "save_employees",
    "save_events",
    "write_txt",
]
