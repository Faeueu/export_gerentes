"""
Lógica de validação, formatação e geração de registros no Modelo 35 da Senior.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .constants import COMPANIES
from .models import Employee


def is_ascii_digits(value: str) -> bool:
    """Verifica se uma string é composta exclusivamente por dígitos ASCII (0-9)."""
    return re.fullmatch(r"[0-9]+", value) is not None


def normalize_company(text: str) -> str:
    """Normaliza o código da empresa com 4 dígitos (0018 ou 0019)."""
    digits = text.strip()
    if not is_ascii_digits(digits) or len(digits) > 4 or int(digits or "0") == 0:
        raise ValueError("A empresa deve ter de 1 a 4 dígitos e ser maior que zero.")
    company = digits.zfill(4)
    if company not in COMPANIES:
        raise ValueError("A empresa deve ser 0018 (Lojão) ou 0019 (Ideal Serviço).")
    return company


def normalize_registration(text: str) -> str:
    """Normaliza a matrícula do colaborador completando com zeros até 9 dígitos."""
    digits = text.strip()
    if not is_ascii_digits(digits) or len(digits) > 9 or int(digits or "0") == 0:
        raise ValueError("A matrícula deve ter de 1 a 9 dígitos e ser maior que zero.")
    return digits.zfill(9)


def normalize_event_code(text: str) -> str:
    """Normaliza o código do evento da folha com 4 dígitos."""
    digits = text.strip()
    if not is_ascii_digits(digits) or len(digits) > 4 or int(digits or "0") == 0:
        raise ValueError("O código do evento deve ter de 1 a 4 dígitos e ser maior que zero.")
    return digits.zfill(4)


def normalize_calculation_code(text: str) -> str:
    """Normaliza o código de cálculo da folha com 5 dígitos."""
    digits = text.strip()
    if not is_ascii_digits(digits) or len(digits) > 5 or int(digits or "0") == 0:
        raise ValueError("O código do cálculo deve ter de 1 a 5 dígitos e ser maior que zero.")
    return digits.zfill(5)


def parse_currency_to_cents(text: str) -> int:
    """Converte valor em formato monetário brasileiro para centavos inteiros."""
    cleaned = text.strip().upper().replace("R$", "").replace(" ", "")
    if not cleaned:
        return 0
    brazilian_grouped = re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{1,2})?", cleaned)
    simple_value = re.fullmatch(r"[0-9]+(?:[,.][0-9]{1,2})?", cleaned)
    if not brazilian_grouped and not simple_value:
        raise ValueError("Use um valor como 1250,50, com no máximo duas casas decimais.")
    normalized = (
        cleaned.replace(".", "").replace(",", ".")
        if brazilian_grouped
        else cleaned.replace(",", ".")
    )
    try:
        value = Decimal(normalized)
        cents = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise ValueError("Use um valor como 1250,50.") from exc
    if not value.is_finite():
        raise ValueError("Use um valor monetário válido.")
    if cents > 99_999_999_999:
        raise ValueError("O valor ultrapassa o limite de 11 posições do leiaute.")
    return cents


def format_cents(cents: int, include_symbol: bool = False) -> str:
    """Formata valor em centavos para texto em padrão brasileiro (ex: '1.250,50' ou 'R$ 1.250,50')."""
    integer, decimals = divmod(cents, 100)
    integer_text = f"{integer:,}".replace(",", ".")
    value = f"{integer_text},{decimals:02d}"
    return f"R$ {value}" if include_symbol else value


def build_record(employee: Employee, calculation_code: str, event_code: str, cents: int) -> str:
    """
    Monta a linha de 62 caracteres exigida pelo Modelo 35 da Senior:
    Posição 01-02: Tipo registro ("01")
    Posição 03-06: Código empresa (4 posições)
    Posição 07-07: Tipo colaborador ("1")
    Posição 08-16: Matrícula colaborador (9 posições)
    Posição 17-21: Código cálculo (5 posições)
    Posição 22-24: Tipo evento ("019")
    Posição 25-28: Código evento (4 posições)
    Posição 29-37: Zeros / complemento ("000000000")
    Posição 38-39: Origem ("01")
    Posição 40-50: Zeros / referência ("00000000000")
    Posição 51-61: Valor em centavos (11 posições)
    Posição 62-62: Indicador inclusão ("I")
    """
    calculation = normalize_calculation_code(calculation_code)
    event = normalize_event_code(event_code)
    if (
        not is_ascii_digits(employee.empresa)
        or len(employee.empresa) != 4
        or employee.empresa not in COMPANIES
        or not is_ascii_digits(employee.matricula)
        or len(employee.matricula) != 9
        or int(employee.matricula) == 0
    ):
        raise ValueError("Empresa ou matrícula do funcionário não atende ao leiaute.")
    if cents <= 0:
        raise ValueError("Evento e valor precisam ser válidos para gerar o lançamento.")

    record = (
        "01"
        + employee.empresa
        + "1"
        + employee.matricula
        + calculation
        + "019"
        + event
        + "000000000"
        + "01"
        + "00000000000"
        + str(cents).zfill(11)
        + "I"
    )
    if len(record) != 62:
        raise ValueError("A linha gerada não possui as 62 posições exigidas pelo Modelo 35.")
    return record


def write_txt(path: Path, records: list[str]) -> None:
    """Grava as linhas no arquivo de texto em padrão ASCII e final de linha CRLF."""
    for record in records:
        if len(record) != 62:
            raise ValueError("Há uma linha com tamanho diferente de 62 posições.")
    with path.open("w", encoding="ascii", newline="") as destination:
        destination.write("\r\n".join(records) + "\r\n")
