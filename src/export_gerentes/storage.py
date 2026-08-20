"""
Gerenciamento seguro de persistência de dados (colaboradores e eventos).
Garante que o executável empacotado armazene os dados internamente no AppData
sem expor planilhas/CSVs para edição acidental pelo usuário final.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import sys
from pathlib import Path

from .constants import EMPLOYEE_COLUMNS, EVENT_COLUMNS
from .generator import (
    normalize_company,
    normalize_event_code,
    normalize_registration,
)
from .models import (
    DEFAULT_EVENTS,
    Employee,
    EmployeeFileError,
    EventFileError,
    PayrollEvent,
)


def get_bundle_directory() -> Path:
    """Retorna o diretório temporário de recursos embutidos pelo PyInstaller (sys._MEIPASS) ou pasta local."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent.parent.parent


def get_data_directory() -> Path:
    """
    Retorna o diretório onde os dados da aplicação são persistidos.
    Em modo empacotado (.exe), utiliza %APPDATA%/ExportGerentes para proteger os dados.
    Em modo desenvolvimento, utiliza a pasta do projeto.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        base = Path(appdata) if appdata else Path.home()
        data_dir = base / "ExportGerentes"
        data_dir.mkdir(parents=True, exist_ok=True)
        _seed_bundled_data_if_missing(data_dir)
        return data_dir

    return Path(__file__).resolve().parent.parent.parent


def _seed_bundled_data_if_missing(target_dir: Path) -> None:
    """Copia os arquivos padrão embutidos no .exe para o diretório de dados caso ainda não existam."""
    bundle_dir = get_bundle_directory()
    for filename in ("colaboradores.csv", "eventos.csv"):
        dest = target_dir / filename
        if not dest.exists():
            bundled_source = bundle_dir / filename
            if bundled_source.exists():
                try:
                    shutil.copy2(bundled_source, dest)
                except OSError:
                    pass


def get_employees_file_path() -> Path:
    return get_data_directory() / "colaboradores.csv"


def get_events_file_path() -> Path:
    return get_data_directory() / "eventos.csv"


def _decode_csv(path: Path, description: str) -> str:
    """Lê arquivo CSV tentando UTF-8 com BOM e recuando para CP1252 se necessário."""
    try:
        raw_content = path.read_bytes()
    except OSError as exc:
        raise ValueError(
            f"Não foi possível ler {path.name}. Feche o arquivo caso esteja aberto e tente novamente."
        ) from exc
    try:
        return raw_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return raw_content.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise ValueError(f"O arquivo de {description} possui codificação inválida.") from exc


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """Escreve dados em CSV com gravação atômica via arquivo temporário."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(columns)
    writer.writerows(rows)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8-sig", newline="") as destination:
            destination.write(buffer.getvalue())
        temporary.replace(path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(
            f"Não foi possível salvar {path.name}. Verifique as permissões e tente novamente."
        ) from exc


def employee_file_has_legacy_branch(path: Path | None = None) -> bool:
    target = path or get_employees_file_path()
    if not target.exists():
        return False
    content = _decode_csv(target, "funcionários")
    first_line = content.splitlines()[0] if content.splitlines() else ""
    return "filial" in {column.strip().lower() for column in first_line.split(";")}


def load_employees(path: Path | None = None) -> list[Employee]:
    target = path or get_employees_file_path()
    if not target.exists():
        # Se não existe no AppData mas existe embutido, tenta ler do bundle
        bundle_source = get_bundle_directory() / "colaboradores.csv"
        if bundle_source.exists():
            target = bundle_source
        else:
            raise EmployeeFileError(
                f"O arquivo {target.name} não foi encontrado."
            )

    try:
        content = _decode_csv(target, "funcionários")
        reader = csv.DictReader(io.StringIO(content, newline=""), delimiter=";")
        if reader.fieldnames:
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
        columns = tuple(reader.fieldnames or ())
        missing = [column for column in EMPLOYEE_COLUMNS if column not in columns]
        if missing:
            raise EmployeeFileError(
                "O cadastro não possui todas as colunas obrigatórias: "
                + ", ".join(missing)
                + "."
            )

        employees: list[Employee] = []
        errors: list[str] = []
        seen: set[tuple[str, str]] = set()
        for line_number, row in enumerate(reader, start=2):
            if not any((row.get(column) or "").strip() for column in EMPLOYEE_COLUMNS):
                continue

            company_text = (row.get("empresa") or "").strip()
            name = (row.get("nome") or "").strip()
            registration_text = (row.get("matricula") or "").strip()
            role = (row.get("funcao") or "").strip()
            line_errors: list[str] = []
            try:
                company = normalize_company(company_text)
            except ValueError as exc:
                company = company_text
                line_errors.append(str(exc))
            try:
                registration = normalize_registration(registration_text)
            except ValueError:
                registration = registration_text
                line_errors.append("matrícula deve ter de 1 a 9 dígitos e ser maior que zero")
            if not name:
                line_errors.append("nome vazio")
            if not role:
                line_errors.append("função vazia")
            if line_errors:
                errors.append(f"Linha {line_number}: " + "; ".join(line_errors))
                continue

            employee = Employee(company, name, registration, role)
            if employee.key in seen:
                errors.append(
                    f"Linha {line_number}: empresa {employee.empresa} e matrícula "
                    f"{employee.matricula} já aparecem no cadastro"
                )
                continue
            seen.add(employee.key)
            employees.append(employee)
    except csv.Error as exc:
        raise EmployeeFileError(
            "O cadastro não pôde ser lido como CSV separado por ponto e vírgula."
        ) from exc
    except ValueError as exc:
        if isinstance(exc, EmployeeFileError):
            raise
        raise EmployeeFileError(str(exc)) from exc

    if errors:
        detail = "\n".join(errors[:12])
        if len(errors) > 12:
            detail += f"\n… e mais {len(errors) - 12} problema(s)."
        raise EmployeeFileError("Corrija o arquivo colaboradores.csv:\n\n" + detail)
    return sorted(employees, key=lambda item: (item.empresa, item.nome.casefold()))


def save_employees(employees: list[Employee], path: Path | None = None) -> None:
    target = path or get_employees_file_path()
    rows = [
        (employee.empresa, employee.nome, employee.matricula, employee.funcao)
        for employee in sorted(employees, key=lambda item: (item.empresa, item.nome.casefold()))
    ]
    try:
        _write_csv(target, EMPLOYEE_COLUMNS, rows)
    except ValueError as exc:
        raise EmployeeFileError(str(exc)) from exc


def load_events(path: Path | None = None) -> list[PayrollEvent]:
    target = path or get_events_file_path()
    if not target.exists():
        bundle_source = get_bundle_directory() / "eventos.csv"
        if bundle_source.exists():
            target = bundle_source
        else:
            return list(DEFAULT_EVENTS)
    try:
        content = _decode_csv(target, "eventos")
        reader = csv.DictReader(io.StringIO(content, newline=""), delimiter=";")
        if reader.fieldnames:
            reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
        columns = tuple(reader.fieldnames or ())
        missing = [column for column in EVENT_COLUMNS if column not in columns]
        if missing:
            raise EventFileError(
                "O cadastro de eventos não possui as colunas: " + ", ".join(missing) + "."
            )

        loaded: list[PayrollEvent] = []
        errors: list[str] = []
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            code_text = (row.get("codigo") or "").strip()
            name = (row.get("nome") or "").strip()
            if not code_text and not name:
                continue
            try:
                code = normalize_event_code(code_text)
            except ValueError:
                errors.append(f"Linha {line_number}: código deve ter de 1 a 4 dígitos")
                continue
            if not name:
                errors.append(f"Linha {line_number}: nome vazio")
                continue
            if code in seen:
                errors.append(f"Linha {line_number}: evento {code} duplicado")
                continue
            seen.add(code)
            loaded.append(PayrollEvent(code, name))
    except csv.Error as exc:
        raise EventFileError(
            "O cadastro de eventos não pôde ser lido como CSV separado por ponto e vírgula."
        ) from exc
    except ValueError as exc:
        if isinstance(exc, EventFileError):
            raise
        raise EventFileError(str(exc)) from exc

    if errors:
        detail = "\n".join(errors[:12])
        if len(errors) > 12:
            detail += f"\n… e mais {len(errors) - 12} problema(s)."
        raise EventFileError("Corrija o arquivo eventos.csv:\n\n" + detail)

    default_codes = {event.codigo for event in DEFAULT_EVENTS}
    custom_events = [event for event in loaded if event.codigo not in default_codes]
    return [*DEFAULT_EVENTS, *custom_events]


def save_events(events: list[PayrollEvent], path: Path | None = None) -> None:
    target = path or get_events_file_path()
    rows = [(event.codigo, event.nome) for event in events]
    try:
        _write_csv(target, EVENT_COLUMNS, rows)
    except ValueError as exc:
        raise EventFileError(str(exc)) from exc
