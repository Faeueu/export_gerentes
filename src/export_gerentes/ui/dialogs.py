"""
Janelas de diálogo modais: Adicionar Colaborador, Adicionar Evento e Prévia de Lançamentos.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..constants import CANVAS, COMPANIES, SURFACE
from ..generator import (
    format_cents,
    normalize_company,
    normalize_event_code,
    normalize_registration,
)
from ..models import Employee, EmployeeFileError, EventFileError, Launch, PayrollEvent
from ..storage import save_employees, save_events


def show_add_employee_dialog(
    parent: tk.Tk | tk.Toplevel,
    current_employees: list[Employee],
    on_employee_added: Callable[[Employee, list[Employee]], None],
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Adicionar gerente ou subgerente")
    dialog.resizable(False, False)
    dialog.configure(background=CANVAS)
    dialog.transient(parent)
    dialog.grab_set()

    content = ttk.Frame(dialog, style="Surface.TFrame", padding=20)
    content.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    content.columnconfigure(1, weight=1)

    company_var = tk.StringVar(value="0018 — Lojão")
    name_var = tk.StringVar()
    registration_var = tk.StringVar()
    role_var = tk.StringVar(value="Gerente")

    fields = (("Empresa", 0), ("Nome", 1), ("Matrícula", 2), ("Função", 3))
    for label, row in fields:
        ttk.Label(content, text=label, background=SURFACE).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=7
        )

    company = ttk.Combobox(
        content,
        textvariable=company_var,
        state="readonly",
        width=32,
        values=tuple(f"{code} — {name}" for code, name in COMPANIES.items()),
    )
    company.grid(row=0, column=1, sticky="ew", pady=7)

    name = ttk.Entry(content, textvariable=name_var, width=42)
    name.grid(row=1, column=1, sticky="ew", pady=7)

    registration = ttk.Entry(content, textvariable=registration_var)
    registration.grid(row=2, column=1, sticky="ew", pady=7)

    role = ttk.Combobox(
        content,
        textvariable=role_var,
        values=("Gerente", "Subgerente", "Ideal Serviços"),
        state="normal",
    )
    role.grid(row=3, column=1, sticky="ew", pady=7)

    hint = ttk.Label(
        content,
        text="A matrícula será completada com zeros à esquerda até 9 dígitos.",
        style="Muted.TLabel",
        background=SURFACE,
    )
    hint.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 12))

    buttons = ttk.Frame(content, style="Surface.TFrame")
    buttons.grid(row=5, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Cancelar", command=dialog.destroy).grid(row=0, column=0, padx=(0, 8))

    def save() -> None:
        try:
            company_code = normalize_company(company_var.get().split("—", 1)[0].strip())
            registration_code = normalize_registration(registration_var.get())
            employee_name = " ".join(name_var.get().split())
            employee_role = " ".join(role_var.get().split())
            if not employee_name:
                raise ValueError("Informe o nome do funcionário.")
            if not employee_role:
                raise ValueError("Informe a função do funcionário.")
            employee = Employee(company_code, employee_name, registration_code, employee_role)
            if employee.key in {item.key for item in current_employees}:
                raise ValueError(
                    f"A matrícula {registration_code} já está cadastrada na empresa {company_code}."
                )
            updated = [*current_employees, employee]
            save_employees(updated)
        except (ValueError, EmployeeFileError) as exc:
            messagebox.showwarning("Não foi possível adicionar", str(exc), parent=dialog)
            return

        dialog.destroy()
        on_employee_added(employee, updated)

    ttk.Button(buttons, text="Adicionar", style="Primary.TButton", command=save).grid(row=0, column=1)
    name.bind("<Return>", lambda _event: (registration.focus_set(), "break")[1])
    registration.bind("<Return>", lambda _event: (role.focus_set(), "break")[1])
    role.bind("<Return>", lambda _event: (save(), "break")[1])
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.wait_visibility()
    name.focus_set()


def show_add_event_dialog(
    parent: tk.Tk | tk.Toplevel,
    current_events: list[PayrollEvent],
    on_event_added: Callable[[PayrollEvent, list[PayrollEvent]], None],
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Adicionar evento")
    dialog.resizable(False, False)
    dialog.configure(background=CANVAS)
    dialog.transient(parent)
    dialog.grab_set()

    content = ttk.Frame(dialog, style="Surface.TFrame", padding=20)
    content.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    content.columnconfigure(1, weight=1)

    code_var = tk.StringVar()
    name_var = tk.StringVar()

    ttk.Label(content, text="Código do evento", background=SURFACE).grid(
        row=0, column=0, sticky="w", padx=(0, 12), pady=7
    )
    code = ttk.Entry(content, textvariable=code_var, width=28)
    code.grid(row=0, column=1, sticky="ew", pady=7)

    ttk.Label(content, text="Nome do evento", background=SURFACE).grid(
        row=1, column=0, sticky="w", padx=(0, 12), pady=7
    )
    name = ttk.Entry(content, textvariable=name_var, width=38)
    name.grid(row=1, column=1, sticky="ew", pady=7)

    ttk.Label(
        content,
        text="O código será completado com zeros à esquerda até 4 dígitos.",
        style="Muted.TLabel",
        background=SURFACE,
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 12))

    buttons = ttk.Frame(content, style="Surface.TFrame")
    buttons.grid(row=3, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="Cancelar", command=dialog.destroy).grid(row=0, column=0, padx=(0, 8))

    def save() -> None:
        try:
            event_code = normalize_event_code(code_var.get())
            event_name = " ".join(name_var.get().split())
            if not event_name:
                raise ValueError("Informe o nome do evento.")
            if event_code in {event.codigo for event in current_events}:
                raise ValueError(f"O evento {event_code} já está cadastrado.")
            event = PayrollEvent(event_code, event_name)
            updated = [*current_events, event]
            save_events(updated)
        except (ValueError, EventFileError) as exc:
            messagebox.showwarning("Não foi possível adicionar", str(exc), parent=dialog)
            return

        dialog.destroy()
        on_event_added(event, updated)

    ttk.Button(buttons, text="Adicionar", style="Primary.TButton", command=save).grid(row=0, column=1)
    code.bind("<Return>", lambda _event: (name.focus_set(), "break")[1])
    name.bind("<Return>", lambda _event: (save(), "break")[1])
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.wait_visibility()
    code.focus_set()


def show_preview_dialog(
    parent: tk.Tk | tk.Toplevel,
    calculation: str,
    launches: list[Launch],
) -> None:
    window = tk.Toplevel(parent)
    window.title(f"Prévia dos lançamentos — cálculo {calculation}")
    window.geometry("1180x560")
    window.minsize(900, 420)
    window.configure(background=CANVAS)
    window.transient(parent)

    ttk.Label(
        window,
        text=f"{len(launches)} lançamento(s) serão incluídos no TXT.",
        font=("Segoe UI Semibold", 12),
    ).pack(anchor="w", padx=16, pady=(16, 10))

    columns = ("nome", "empresa", "matricula", "evento", "valor", "linha")
    preview_frame = ttk.Frame(window, style="Surface.TFrame")
    preview_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
    preview_frame.rowconfigure(0, weight=1)
    preview_frame.columnconfigure(0, weight=1)

    tree = ttk.Treeview(preview_frame, columns=columns, show="headings")
    headings = {
        "nome": "Funcionário",
        "empresa": "Empresa",
        "matricula": "Matrícula",
        "evento": "Evento",
        "valor": "Valor",
        "linha": "Linha Modelo 35 (62 posições)",
    }
    widths = {
        "nome": 260,
        "empresa": 70,
        "matricula": 95,
        "evento": 210,
        "valor": 95,
        "linha": 520,
    }
    for column in columns:
        tree.heading(column, text=headings[column])
        tree.column(column, width=widths[column], minwidth=widths[column], anchor="w")

    tree.column("empresa", anchor="center")
    tree.column("matricula", anchor="center")
    tree.column("valor", anchor="e")

    vertical = ttk.Scrollbar(preview_frame, orient="vertical", command=tree.yview)
    horizontal = ttk.Scrollbar(preview_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    for launch in launches:
        tree.insert(
            "",
            "end",
            values=(
                launch.employee.nome,
                launch.employee.empresa,
                launch.employee.matricula,
                f"{launch.event_code} — {launch.event_name}",
                format_cents(launch.cents, include_symbol=True),
                launch.record,
            ),
        )
