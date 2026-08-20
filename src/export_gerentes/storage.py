from __future__ import annotations

import csv
import io
import os
import shutil
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from .constants import EMPLOYEE_COLUMNS, EVENT_COLUMNS
from .generator import (
    format_cents,
    normalize_company,
    normalize_event_code,
    normalize_registration,
    parse_currency_to_cents,
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
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass is not None:
        return Path(meipass).resolve()
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
    for filename in ("colaboradores.csv", "eventos.csv", "valores.csv"):
        dest = target_dir / filename
        if not dest.exists():
            bundled_source = bundle_dir / filename
            if not bundled_source.exists():
                bundled_source = bundle_dir / filename.replace(".csv", "_exemplo.csv")
            if bundled_source.exists():
                try:
                    shutil.copy2(bundled_source, dest)
                except OSError:
                    pass


def get_employees_file_path() -> Path:
    return get_data_directory() / "colaboradores.csv"


def get_events_file_path() -> Path:
    return get_data_directory() / "eventos.csv"


def get_values_file_path() -> Path:
    return get_data_directory() / "valores.csv"


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


def _write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Sequence[str]],
) -> None:
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
    if path is not None:
        target = path
        if not target.exists():
            raise EmployeeFileError(f"O arquivo {target.name} não foi encontrado.")
    else:
        target = get_employees_file_path()
        if not target.exists():
            bundle_source = get_bundle_directory() / "colaboradores.csv"
            if bundle_source.exists():
                target = bundle_source
            else:
                example_source = get_bundle_directory() / "colaboradores_exemplo.csv"
                if example_source.exists():
                    target = example_source
                else:
                    return []

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
    if path is not None:
        target = path
        if not target.exists():
            return list(DEFAULT_EVENTS)
    else:
        target = get_events_file_path()
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


def load_values(
    employees: list[Employee],
    events: list[PayrollEvent],
    path: Path | None = None,
) -> dict[tuple[str, str, str], int]:
    """
    Carrega os valores preenchidos salvos em valores.csv.
    Retorna um dicionário {(empresa, matricula, codigo_evento): valor_em_centavos}.
    """
    if path is not None:
        target = path
        if not target.exists():
            return {}
    else:
        target = get_values_file_path()
        if not target.exists():
            bundle_source = get_bundle_directory() / "valores.csv"
            if bundle_source.exists():
                target = bundle_source
            else:
                return {}

    try:
        content = _decode_csv(target, "valores")
        reader = csv.DictReader(io.StringIO(content, newline=""), delimiter=";")
        if not reader.fieldnames:
            return {}

        # Mapeia colunas para códigos de eventos
        event_by_code = {event.codigo: event.codigo for event in events}
        event_by_name = {event.nome.casefold(): event.codigo for event in events}
        column_map: dict[str, str] = {}

        for raw_col in reader.fieldnames:
            col_cleaned = raw_col.strip()
            # Se for código de evento normalizado
            try:
                norm = normalize_event_code(col_cleaned)
                if norm in event_by_code:
                    column_map[raw_col] = norm
                    continue
            except ValueError:
                pass
            if col_cleaned.casefold() in event_by_name:
                column_map[raw_col] = event_by_name[col_cleaned.casefold()]

        values: dict[tuple[str, str, str], int] = {}
        for row in reader:
            emp_text = (row.get("empresa") or "").strip()
            mat_text = (row.get("matricula") or "").strip()
            if not emp_text or not mat_text:
                continue
            try:
                emp = normalize_company(emp_text)
                mat = normalize_registration(mat_text)
            except ValueError:
                continue

            for col_name, event_code in column_map.items():
                val_text = (row.get(col_name) or "").strip()
                if not val_text:
                    continue
                try:
                    cents = parse_currency_to_cents(val_text)
                    if cents > 0:
                        values[(emp, mat, event_code)] = cents
                except ValueError:
                    pass

        return values
    except Exception:
        return {}


def save_values(
    employees: list[Employee],
    events: list[PayrollEvent],
    values: dict[tuple[str, str, str], int],
    path: Path | None = None,
) -> None:
    """
    Persiste o estado atual dos valores da tabela em valores.csv.
    """
    target = path or get_values_file_path()
    event_codes = [event.codigo for event in events]
    columns = ["empresa", "nome", "matricula", "funcao", *event_codes]
    rows: list[list[str]] = []

    for emp in sorted(employees, key=lambda item: (item.empresa, item.nome.casefold())):
        row_values = [
            format_cents(values.get((emp.empresa, emp.matricula, code), 0))
            for code in event_codes
        ]
        rows.append([emp.empresa, emp.nome, emp.matricula, emp.funcao, *row_values])

    try:
        _write_csv(target, columns, rows)
    except Exception:
        pass
