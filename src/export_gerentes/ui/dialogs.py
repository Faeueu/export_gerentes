"""
Janelas de diálogo modais: Adicionar/Gerenciar Colaboradores, Adicionar/Gerenciar Eventos e Prévia de Lançamentos.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ..constants import CANVAS, COMPANIES, ERROR, MUTED, SURFACE
from ..generator import (
    format_cents,
    normalize_company,
    normalize_event_code,
    normalize_registration,
)
from ..models import (
    DEFAULT_EVENTS,
    Employee,
    EmployeeFileError,
    EventFileError,
    Launch,
    PayrollEvent,
)
from ..storage import get_data_directory, save_employees, save_events


def _open_data_folder() -> None:
    """Abre o diretório onde os dados estão salvos no Explorer do Windows."""
    data_dir = get_data_directory()
    try:
        if sys.platform == "win32":
            os.startfile(str(data_dir))
        else:
            subprocess.run(["xdg-open", str(data_dir)])
    except Exception as exc:
        messagebox.showinfo("Diretório de Dados", f"Os dados estão salvos em:\n\n{data_dir}\n\nDetalhe: {exc}")


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


def show_manage_employees_dialog(
    parent: tk.Tk | tk.Toplevel,
    get_employees: Callable[[], list[Employee]],
    on_employees_changed: Callable[[list[Employee]], None],
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Gerenciar Gerentes e Colaboradores")
    dialog.geometry("820x520")
    dialog.minsize(700, 400)
    dialog.configure(background=CANVAS)
    dialog.transient(parent)
    dialog.grab_set()

    top_bar = ttk.Frame(dialog, style="Surface.TFrame", padding=(16, 12))
    top_bar.pack(fill="x", padx=16, pady=(16, 8))
    top_bar.columnconfigure(1, weight=1)

    ttk.Label(top_bar, text="Buscar:", background=SURFACE).grid(row=0, column=0, padx=(0, 8))
    search_var = tk.StringVar()
    search_entry = ttk.Entry(top_bar, textvariable=search_var, width=28)
    search_entry.grid(row=0, column=1, sticky="w")

    btn_frame = ttk.Frame(top_bar, style="Surface.TFrame")
    btn_frame.grid(row=0, column=2, sticky="e")

    tree_frame = ttk.Frame(dialog, style="Surface.TFrame")
    tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    columns = ("empresa", "nome", "matricula", "funcao")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
    tree.heading("empresa", text="Empresa")
    tree.heading("nome", text="Nome")
    tree.heading("matricula", text="Matrícula")
    tree.heading("funcao", text="Função")

    tree.column("empresa", width=80, anchor="center")
    tree.column("nome", width=340, anchor="w")
    tree.column("matricula", width=120, anchor="center")
    tree.column("funcao", width=160, anchor="w")

    vertical = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vertical.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")

    bottom_bar = ttk.Frame(dialog, style="Surface.TFrame", padding=(16, 10))
    bottom_bar.pack(fill="x", padx=16, pady=(0, 16))
    status_label = ttk.Label(bottom_bar, text="", background=SURFACE, style="Muted.TLabel")
    status_label.pack(side="left")

    ttk.Button(
        bottom_bar,
        text="📂 Abrir pasta dos dados",
        style="Secondary.TButton",
        command=_open_data_folder,
    ).pack(side="right", padx=(8, 0))

    def refresh_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)
        query = search_var.get().strip().casefold()
        all_emp = get_employees()
        filtered = [
            e
            for e in all_emp
            if not query
            or query in e.nome.casefold()
            or query in e.matricula
            or query in e.funcao.casefold()
            or query in e.empresa
        ]
        for emp in filtered:
            tree.insert("", "end", iid=f"{emp.empresa}_{emp.matricula}", values=(emp.empresa, emp.nome, emp.matricula, emp.funcao))
        status_label.config(text=f"{len(filtered)} colaborador(es) exibido(s) de {len(all_emp)} cadastrados.")

    search_var.trace_add("write", lambda *_: refresh_tree())

    def delete_selected() -> None:
        selected_id = tree.focus()
        if not selected_id:
            messagebox.showwarning("Atenção", "Selecione um funcionário na lista para excluir.", parent=dialog)
            return
        company_code, reg = selected_id.split("_", 1)
        all_emp = get_employees()
        emp_to_del = next((e for e in all_emp if e.empresa == company_code and e.matricula == reg), None)
        if not emp_to_del:
            return

        confirm = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente remover o colaborador abaixo do cadastro?\n\n"
            f"Nome: {emp_to_del.nome}\n"
            f"Empresa: {emp_to_del.empresa}\n"
            f"Matrícula: {emp_to_del.matricula}\n"
            f"Função: {emp_to_del.funcao}",
            parent=dialog,
        )
        if not confirm:
            return

        updated = [e for e in all_emp if not (e.empresa == company_code and e.matricula == reg)]
        try:
            save_employees(updated)
        except EmployeeFileError as exc:
            messagebox.showerror("Erro ao salvar", str(exc), parent=dialog)
            return

        on_employees_changed(updated)
        refresh_tree()
        messagebox.showinfo("Sucesso", f"O colaborador {emp_to_del.nome} foi removido com sucesso.", parent=dialog)

    def add_new() -> None:
        def on_added(new_emp: Employee, updated_list: list[Employee]) -> None:
            on_employees_changed(updated_list)
            refresh_tree()
            tree.selection_set(f"{new_emp.empresa}_{new_emp.matricula}")
            tree.see(f"{new_emp.empresa}_{new_emp.matricula}")

        show_add_employee_dialog(dialog, get_employees(), on_added)

    ttk.Button(btn_frame, text="+ Novo colaborador", style="Primary.TButton", command=add_new).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(btn_frame, text="🗑️ Excluir selecionado", style="Secondary.TButton", command=delete_selected).pack(
        side="left"
    )

    refresh_tree()


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


def show_manage_events_dialog(
    parent: tk.Tk | tk.Toplevel,
    get_events: Callable[[], list[PayrollEvent]],
    on_events_changed: Callable[[list[PayrollEvent]], None],
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Gerenciar Eventos da Folha")
    dialog.geometry("640x440")
    dialog.minsize(540, 350)
    dialog.configure(background=CANVAS)
    dialog.transient(parent)
    dialog.grab_set()

    top_bar = ttk.Frame(dialog, style="Surface.TFrame", padding=(16, 12))
    top_bar.pack(fill="x", padx=16, pady=(16, 8))
    top_bar.columnconfigure(0, weight=1)

    btn_frame = ttk.Frame(top_bar, style="Surface.TFrame")
    btn_frame.grid(row=0, column=0, sticky="e")

    tree_frame = ttk.Frame(dialog, style="Surface.TFrame")
    tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    columns = ("codigo", "nome", "tipo")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
    tree.heading("codigo", text="Código")
    tree.heading("nome", text="Nome do Evento")
    tree.heading("tipo", text="Tipo")

    tree.column("codigo", width=80, anchor="center")
    tree.column("nome", width=340, anchor="w")
    tree.column("tipo", width=120, anchor="center")

    vertical = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vertical.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")

    bottom_bar = ttk.Frame(dialog, style="Surface.TFrame", padding=(16, 10))
    bottom_bar.pack(fill="x", padx=16, pady=(0, 16))
    status_label = ttk.Label(bottom_bar, text="", background=SURFACE, style="Muted.TLabel")
    status_label.pack(side="left")

    ttk.Button(
        bottom_bar,
        text="📂 Abrir pasta dos dados",
        style="Secondary.TButton",
        command=_open_data_folder,
    ).pack(side="right", padx=(8, 0))

    default_codes = {e.codigo for e in DEFAULT_EVENTS}

    def refresh_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)
        all_ev = get_events()
        for ev in all_ev:
            is_def = ev.codigo in default_codes
            tipo = "Padrão" if is_def else "Personalizado"
            tree.insert("", "end", iid=ev.codigo, values=(ev.codigo, ev.nome, tipo))
        status_label.config(text=f"{len(all_ev)} evento(s) configurado(s).")

    def delete_selected() -> None:
        selected_code = tree.focus()
        if not selected_code:
            messagebox.showwarning("Atenção", "Selecione um evento na lista para excluir.", parent=dialog)
            return
        if selected_code in default_codes:
            messagebox.showinfo(
                "Evento Padrão",
                "Os eventos padrão do Modelo 35 (0816, 0239, 1074, 1102) não podem ser excluídos.",
                parent=dialog,
            )
            return

        all_ev = get_events()
        ev_to_del = next((e for e in all_ev if e.codigo == selected_code), None)
        if not ev_to_del:
            return

        confirm = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente remover o evento {ev_to_del.codigo} — {ev_to_del.nome}?",
            parent=dialog,
        )
        if not confirm:
            return

        updated = [e for e in all_ev if e.codigo != selected_code]
        try:
            save_events(updated)
        except EventFileError as exc:
            messagebox.showerror("Erro ao salvar", str(exc), parent=dialog)
            return

        on_events_changed(updated)
        refresh_tree()
        messagebox.showinfo("Sucesso", f"O evento {ev_to_del.nome} foi removido.", parent=dialog)

    def add_new() -> None:
        def on_added(new_ev: PayrollEvent, updated_list: list[PayrollEvent]) -> None:
            on_events_changed(updated_list)
            refresh_tree()
            tree.selection_set(new_ev.codigo)
            tree.see(new_ev.codigo)

        show_add_event_dialog(dialog, get_events(), on_added)

    ttk.Button(btn_frame, text="+ Novo evento", style="Primary.TButton", command=add_new).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(btn_frame, text="🗑️ Excluir selecionado", style="Secondary.TButton", command=delete_selected).pack(
        side="left"
    )

    refresh_tree()


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
