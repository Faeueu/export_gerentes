from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Employee:
    empresa: str
    nome: str
    matricula: str
    funcao: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "nome", " ".join(self.nome.split()).upper())
        object.__setattr__(self, "funcao", " ".join(self.funcao.split()).upper())

    @property
    def key(self) -> tuple[str, str]:
        return self.empresa, self.matricula


@dataclass(frozen=True)
class PayrollEvent:
    codigo: str
    nome: str


DEFAULT_EVENTS: tuple[PayrollEvent, ...] = (
    PayrollEvent("0816", "Comissão Produto"),
    PayrollEvent("0239", "Comissão Serviço"),
    PayrollEvent("1074", "Prêmio Produtividade"),
    PayrollEvent("1102", "Prêmio Meta Semanal"),
)


@dataclass(frozen=True)
class Launch:
    employee: Employee
    event_code: str
    event_name: str
    cents: int
    record: str


class EmployeeFileError(ValueError):
    """Erro relacionado à leitura/gravação do cadastro de colaboradores."""
    pass


class EventFileError(ValueError):
    """Erro relacionado à leitura/gravação do cadastro de eventos."""
    pass
