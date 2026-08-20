from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..constants import (
    APP_SUBTITLE,
    APP_TITLE,
    BLUE,
    BORDER,
    CANVAS,
    COMPANIES,
    ERROR,
    ERROR_BG,
    GREEN,
    HEADER_BG,
    INK,
    MIN_EVENT_COL_WIDTH,
    MUTED,
    NAVY,
    ROW_ALT_BG,
    STATIC_WIDTHS,
    SURFACE,
)
from ..generator import (
    build_record,
    format_cents,
    normalize_calculation_code,
    parse_currency_to_cents,
    write_txt,
)
from ..models import (
    DEFAULT_EVENTS,
    Employee,
    EmployeeFileError,
    EventFileError,
    Launch,
    PayrollEvent,
)
from ..storage import (
    employee_file_has_legacy_branch,
    get_data_directory,
    load_employees,
    load_events,
    load_values,
    save_employees,
    save_events,
    save_values,
)
from .dialogs import (
    show_add_employee_dialog,
    show_add_event_dialog,
    show_manage_employees_dialog,
    show_manage_events_dialog,
    show_preview_dialog,
)


class PayrollApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1380x820")
        self.minsize(1080, 650)
        self.configure(background=CANVAS)

        self.employees: list[Employee] = []
        self.events: list[PayrollEvent] = list(DEFAULT_EVENTS)
        self.values: dict[tuple[str, str, str], int] = {}
        self.visible_entries: list[ttk.Entry] = []
        self.entry_context: dict[ttk.Entry, tuple[Employee, str]] = {}
        self._last_canvas_width = 0
        self._resize_job: str | None = None

        default_company = next((f"{code} — {name}" for code, name in COMPANIES.items()), "0018 — Lojão")
        self.status_var = tk.StringVar(value="Carregando cadastros…")
        self.calculation_var = tk.StringVar()
        self.company_filter_var = tk.StringVar(value=default_company)
        self.search_var = tk.StringVar()
        self.people_summary_var = tk.StringVar(value="0 pessoas com valores")
        self.lines_summary_var = tk.StringVar(value="0 eventos para exportar")
        self.total_summary_var = tk.StringVar(value="Total: R$ 0,00")

        self._configure_styles()
        self._build_interface()
        self.reload_files(show_success=False)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=CANVAS)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("TLabel", background=CANVAS, foreground=INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Summary.TLabel", foreground=INK, font=("Segoe UI Semibold", 10))
        style.configure(
            "Header.TLabel",
            background=HEADER_BG,
            foreground=INK,
            font=("Segoe UI Semibold", 9),
            padding=(4, 6),
            anchor="center",
        )
        style.configure("TEntry", fieldbackground=SURFACE, foreground=INK, padding=(7, 5))
        style.configure(
            "Money.TEntry",
            fieldbackground=SURFACE,
            foreground=INK,
            padding=(5, 3),
            font=("Segoe UI", 9),
        )
        style.configure(
            "Invalid.TEntry",
            fieldbackground=ERROR_BG,
            foreground=ERROR,
            padding=(5, 3),
            font=("Segoe UI", 9),
        )
        style.map("TEntry", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)])
        style.map(
            "Money.TEntry",
            bordercolor=[("focus", BLUE)],
            lightcolor=[("focus", BLUE)],
            fieldbackground=[("focus", "#EAF1FF")],
        )
        style.configure("TCombobox", fieldbackground=SURFACE, padding=(6, 5))
        style.configure("Secondary.TButton", font=("Segoe UI Semibold", 9), padding=(10, 7))
        style.configure(
            "Primary.TButton",
            background=GREEN,
            foreground="#FFFFFF",
            bordercolor=GREEN,
            font=("Segoe UI Semibold", 10),
            padding=(16, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#007657"), ("disabled", "#92BFB1")],
            foreground=[("disabled", "#F2F7F5")],
        )

    def _build_interface(self) -> None:
        # Header Top Bar
        header = tk.Frame(self, background=NAVY, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Comissões e Premiações",
            background=NAVY,
            foreground="#FFFFFF",
            font=("Segoe UI Semibold", 17),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(12, 0))

        tk.Label(
            header,
            text=APP_SUBTITLE,
            background=NAVY,
            foreground="#C7D3EA",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))

        # Controls & Filters Card
        controls = ttk.Frame(self, style="Surface.TFrame", padding=(16, 12))
        controls.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 8))
        controls.columnconfigure(6, weight=1)

        ttk.Label(controls, text="Código do cálculo", background=SURFACE).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        self.calculation_entry = ttk.Entry(
            controls, textvariable=self.calculation_var, width=10, justify="center"
        )
        self.calculation_entry.grid(row=0, column=1, sticky="w", padx=(0, 20))
        self.calculation_entry.bind("<FocusOut>", self._format_calculation)
        self.calculation_entry.bind("<Return>", self._start_money_entry)

        ttk.Label(controls, text="Empresa", background=SURFACE).grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        self.company_combo = ttk.Combobox(
            controls,
            textvariable=self.company_filter_var,
            state="readonly",
            width=22,
            values=self._company_filter_options(),
        )
        self.company_combo.grid(row=0, column=3, sticky="w", padx=(0, 20))
        self.company_combo.bind("<<ComboboxSelected>>", lambda _event: self.rebuild_table())

        ttk.Label(controls, text="Buscar funcionário", background=SURFACE).grid(
            row=0, column=4, sticky="w", padx=(0, 8)
        )
        search_entry = ttk.Entry(controls, textvariable=self.search_var, width=26)
        search_entry.grid(row=0, column=5, sticky="w")
        search_entry.bind("<KeyRelease>", lambda _event: self.rebuild_table())

        # Action Buttons Row
        actions = ttk.Frame(controls, style="Surface.TFrame")
        actions.grid(row=1, column=0, columnspan=7, sticky="ew", pady=(12, 0))
        actions.columnconfigure(4, weight=1)

        ttk.Button(
            actions, text="👥 Gerenciar colaboradores", style="Secondary.TButton", command=self.manage_employees
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            actions, text="⚙️ Gerenciar eventos", style="Secondary.TButton", command=self.manage_events
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(
            actions, text="🔄 Recarregar dados", style="Secondary.TButton", command=self.reload_files
        ).grid(row=0, column=2)

        ttk.Button(
            actions,
            text="Visualizar lançamentos",
            style="Secondary.TButton",
            command=self.show_preview,
        ).grid(row=0, column=5, padx=8)
        self.export_button = ttk.Button(
            actions, text="Exportar TXT", style="Primary.TButton", command=self.export_txt
        )
        self.export_button.grid(row=0, column=6, padx=(8, 0))

        # Summary Metrics Bar
        summary = ttk.Frame(self, style="Surface.TFrame", padding=(20, 9))
        summary.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        summary.columnconfigure((0, 2, 4), weight=1)
        ttk.Label(
            summary, textvariable=self.people_summary_var, style="Summary.TLabel", background=SURFACE
        ).grid(row=0, column=0, sticky="w")
        ttk.Separator(summary, orient="vertical").grid(row=0, column=1, sticky="ns", padx=20)
        ttk.Label(
            summary, textvariable=self.lines_summary_var, style="Summary.TLabel", background=SURFACE
        ).grid(row=0, column=2, sticky="w")
        ttk.Separator(summary, orient="vertical").grid(row=0, column=3, sticky="ns", padx=20)
        ttk.Label(
            summary, textvariable=self.total_summary_var, style="Summary.TLabel", background=SURFACE
        ).grid(row=0, column=4, sticky="w")

        # Table Container
        table_shell = ttk.Frame(self, style="Surface.TFrame")
        table_shell.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        table_shell.rowconfigure(1, weight=1)
        table_shell.columnconfigure(0, weight=1)

        # Header Canvas (synchronized horizontal scroll)
        self.header_canvas = tk.Canvas(
            table_shell, background=HEADER_BG, borderwidth=0, highlightthickness=0, height=48
        )
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_frame = tk.Frame(self.header_canvas, background=HEADER_BG)
        self.header_window = self.header_canvas.create_window((0, 0), window=self.header_frame, anchor="nw")

        # Table Body Canvas (horizontal & vertical scroll)
        self.table_canvas = tk.Canvas(
            table_shell, background=SURFACE, borderwidth=0, highlightthickness=0
        )
        vertical = ttk.Scrollbar(table_shell, orient="vertical", command=self.table_canvas.yview)
        self.horizontal = ttk.Scrollbar(table_shell, orient="horizontal", command=self._scroll_x)
        self.table_canvas.configure(yscrollcommand=vertical.set, xscrollcommand=self.horizontal.set)
        self.table_canvas.grid(row=1, column=0, sticky="nsew")
        vertical.grid(row=1, column=1, sticky="ns")
        self.horizontal.grid(row=2, column=0, sticky="ew")

        # Rows Container Grid
        self.rows_frame = tk.Frame(self.table_canvas, background=SURFACE)
        self.rows_window = self.table_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")

        self.rows_frame.bind("<Configure>", self._refresh_table_geometry)
        self.header_frame.bind("<Configure>", self._refresh_table_geometry)
        self.table_canvas.bind("<Configure>", self._on_canvas_configure)
        self.table_canvas.bind("<Enter>", self._activate_mousewheel)
        self.table_canvas.bind("<Leave>", self._deactivate_mousewheel)

        # Bottom Status Bar
        status = tk.Frame(self, background=NAVY, height=28)
        status.grid(row=4, column=0, sticky="ew")
        status.grid_propagate(False)
        tk.Label(
            status,
            textvariable=self.status_var,
            background=NAVY,
            foreground="#D8E1F1",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="both", expand=True, padx=16)

        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        self._rebuild_header()

    def _company_filter_options(self) -> tuple[str, ...]:
        return tuple(f"{code} — {name}" for code, name in COMPANIES.items())

    def selected_company_code(self) -> str:
        company_filter = self.company_filter_var.get()
        return company_filter.split("—", 1)[0].strip()

    def _event_column_width(self) -> int:
        num_events = len(self.events)
        if num_events == 0:
            return MIN_EVENT_COL_WIDTH

        viewport_width = self.table_canvas.winfo_width()
        if viewport_width <= 1:
            viewport_width = 1320

        static_total = sum(STATIC_WIDTHS)
        available_for_events = viewport_width - static_total - 20
        calculated = int(available_for_events / num_events)
        return max(MIN_EVENT_COL_WIDTH, calculated)

    def _content_width(self) -> int:
        return sum(STATIC_WIDTHS) + len(self.events) * self._event_column_width()

    def _column_widths(self) -> tuple[int, ...]:
        event_width = self._event_column_width()
        return (*STATIC_WIDTHS, *(event_width for _ in self.events))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        if event.widget != self.table_canvas:
            self._refresh_table_geometry()
            return

        if abs(event.width - self._last_canvas_width) > 15:
            self._last_canvas_width = event.width
            if self._resize_job is not None:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(50, self._apply_resize)
        else:
            self._refresh_table_geometry()

    def _apply_resize(self) -> None:
        self._resize_job = None
        self._rebuild_header()
        self.rebuild_table()

    def _rebuild_header(self) -> None:
        for child in self.header_frame.winfo_children():
            child.destroy()

        headers = ["Empresa", "Nome", "Matrícula", "Função", *(event.nome for event in self.events)]
        widths = self._column_widths()

        for column, (title, width) in enumerate(zip(headers, widths)):
            is_event = column >= 4
            uniform_group = "event_cols" if is_event else f"c{column}"
            weight = 1 if is_event else 0

            self.header_frame.columnconfigure(
                column, minsize=width, weight=weight, uniform=uniform_group
            )
            cell = tk.Frame(self.header_frame, background=HEADER_BG, height=48)
            cell.grid(row=0, column=column, sticky="nsew", padx=(0, 1))
            cell.grid_propagate(False)

            tk.Label(
                cell,
                text=title,
                background=HEADER_BG,
                foreground=INK,
                font=("Segoe UI Semibold", 9),
                justify="center",
                wraplength=max(width - 14, 60),
            ).place(relx=0.5, rely=0.5, anchor="center", relwidth=0.96)

        self.after_idle(self._refresh_table_geometry)

    def _refresh_table_geometry(self, _event: tk.Event | None = None) -> None:
        width = max(self._content_width(), self.table_canvas.winfo_width(), 1)
        body_height = max(self.rows_frame.winfo_reqheight(), 1)
        self.table_canvas.itemconfigure(self.rows_window, width=width)
        self.table_canvas.configure(scrollregion=(0, 0, width, body_height))
        self.header_canvas.itemconfigure(self.header_window, width=width, height=48)
        self.header_canvas.configure(scrollregion=(0, 0, width, 48))

    def _scroll_x(self, *args: str) -> None:
        self.table_canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _scroll_table(self, event: tk.Event) -> None:
        if self.table_canvas.winfo_exists():
            self.table_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_table_horizontal(self, event: tk.Event) -> str:
        self._scroll_x("scroll", str(int(-1 * (event.delta / 120))), "units")
        return "break"

    def _activate_mousewheel(self, _event: tk.Event) -> None:
        self.bind_all("<MouseWheel>", self._scroll_table)
        self.bind_all("<Shift-MouseWheel>", self._scroll_table_horizontal)

    def _deactivate_mousewheel(self, _event: tk.Event) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Shift-MouseWheel>")

    def _format_calculation(self, _event: tk.Event | None = None) -> None:
        if not self.calculation_var.get().strip():
            return
        try:
            self.calculation_var.set(normalize_calculation_code(self.calculation_var.get()))
        except ValueError:
            pass

    def _start_money_entry(self, _event: tk.Event) -> str:
        try:
            self.calculation_var.set(normalize_calculation_code(self.calculation_var.get()))
        except ValueError as exc:
            self.status_var.set(str(exc))
            self.calculation_entry.focus_set()
            self.calculation_entry.selection_range(0, tk.END)
            return "break"
        if self.visible_entries:
            self._focus_entry(0)
        return "break"

    def reload_files(self, show_success: bool = True) -> None:
        try:
            employees = load_employees()
            events = load_events()
            if employee_file_has_legacy_branch():
                save_employees(employees)
        except (EmployeeFileError, EventFileError) as exc:
            self.status_var.set("Os dados precisam ser corrigidos antes do preenchimento.")
            messagebox.showerror("Não foi possível carregar os cadastros", str(exc), parent=self)
            return

        new_by_key = {employee.key: employee for employee in employees}
        valid_employee_keys = set(new_by_key)
        valid_event_codes = {event.codigo for event in events}
        self.employees = employees
        self.events = events

        loaded_values = load_values(employees, events)
        if not self.values or show_success:
            self.values = loaded_values
        else:
            for key, val in loaded_values.items():
                if key not in self.values:
                    self.values[key] = val

        self.values = {
            key: value
            for key, value in self.values.items()
            if (key[0], key[1]) in valid_employee_keys
            and key[2] in valid_event_codes
        }
        options = self._company_filter_options()
        self.company_combo.configure(values=options)
        if self.company_filter_var.get() not in options and options:
            self.company_filter_var.set(options[0])
        self._rebuild_header()
        self.rebuild_table()

        self.status_var.set(
            f"Cadastros carregados: {len(employees)} funcionário(s) e {len(events)} evento(s)."
        )
        if show_success:
            messagebox.showinfo(
                "Dados recarregados",
                f"{len(employees)} funcionário(s) e {len(events)} evento(s) disponíveis.",
                parent=self,
            )
        self.after_idle(self.calculation_entry.focus_set)

    def manage_employees(self) -> None:
        def on_changed(updated_list: list[Employee]) -> None:
            self.employees = sorted(updated_list, key=lambda item: (item.empresa, item.nome.casefold()))
            save_values(self.employees, self.events, self.values)
            self.rebuild_table()
            self.status_var.set(f"Cadastro atualizado: {len(self.employees)} colaborador(es).")

        show_manage_employees_dialog(self, lambda: self.employees, on_changed)

    def manage_events(self) -> None:
        def on_changed(updated_list: list[PayrollEvent]) -> None:
            self.events = updated_list
            save_values(self.employees, self.events, self.values)
            self._rebuild_header()
            self.rebuild_table()
            self.status_var.set(f"Eventos atualizados: {len(self.events)} configurado(s).")

        show_manage_events_dialog(self, lambda: self.events, on_changed)

    def add_employee(self) -> None:
        self.manage_employees()

    def add_event(self) -> None:
        self.manage_events()

    def _show_row_context_menu(self, event: tk.Event, employee: Employee) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=f"🗑️ Excluir {employee.nome}...",
            command=lambda: self._delete_employee(employee),
        )
        menu.add_separator()
        menu.add_command(
            label="👥 Gerenciar todos os colaboradores...",
            command=self.manage_employees,
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_employee(self, employee: Employee) -> None:
        confirm = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente remover o colaborador abaixo do cadastro?\n\n"
            f"Nome: {employee.nome}\n"
            f"Empresa: {employee.empresa}\n"
            f"Matrícula: {employee.matricula}\n"
            f"Função: {employee.funcao}",
            parent=self,
        )
        if not confirm:
            return

        updated = [e for e in self.employees if e.key != employee.key]
        try:
            save_employees(updated)
        except EmployeeFileError as exc:
            messagebox.showerror("Erro ao salvar", str(exc), parent=self)
            return

        self.employees = updated
        self.values = {k: v for k, v in self.values.items() if (k[0], k[1]) != employee.key}
        save_values(self.employees, self.events, self.values)
        self.rebuild_table()
        self.status_var.set(f"{employee.nome} foi removido do cadastro.")
        messagebox.showinfo("Sucesso", f"O colaborador {employee.nome} foi removido.", parent=self)

    def filtered_employees(self) -> list[Employee]:
        company_code = self.selected_company_code()
        search = self.search_var.get().strip().casefold()
        return [
            employee
            for employee in self.employees
            if (not company_code or employee.empresa == company_code)
            and (
                not search
                or search in employee.nome.casefold()
                or search in employee.matricula
                or search in employee.funcao.casefold()
                or search in employee.empresa
            )
        ]

    def rebuild_table(self) -> None:
        for child in self.rows_frame.winfo_children():
            child.destroy()

        self.visible_entries.clear()
        self.entry_context.clear()
        employees = self.filtered_employees()

        if not employees:
            empty_text = (
                "Nenhum funcionário encontrado para este filtro."
                if self.employees
                else "Clique em “Gerenciar gerentes” para adicionar colaboradores."
            )
            tk.Label(
                self.rows_frame,
                text=empty_text,
                background=SURFACE,
                foreground=MUTED,
                font=("Segoe UI", 11),
                pady=36,
            ).pack(fill="x")
            self._refresh_table_geometry()
            self.update_summary()
            return

        widths = self._column_widths()

        # Configura as colunas de self.rows_frame com uniformidade estrita
        for col_idx, width in enumerate(widths):
            is_event = col_idx >= 4
            uniform_group = "event_cols" if is_event else f"c{col_idx}"
            weight = 1 if is_event else 0
            self.rows_frame.columnconfigure(
                col_idx, minsize=width, weight=weight, uniform=uniform_group
            )

        for row_index, employee in enumerate(employees):
            background = SURFACE if row_index % 2 == 0 else ROW_ALT_BG

            # Coluna 0: Empresa (Apenas código)
            cell_empresa = tk.Frame(self.rows_frame, background=background, height=36)
            cell_empresa.grid(row=row_index, column=0, sticky="nsew", padx=(0, 1), pady=1)
            cell_empresa.grid_propagate(False)
            lbl_empresa = tk.Label(
                cell_empresa,
                text=employee.empresa,
                background=background,
                foreground=INK,
                font=("Segoe UI Semibold", 9),
            )
            lbl_empresa.place(relx=0.5, rely=0.5, anchor="center")

            # Coluna 1: Nome (Alinhado à esquerda com margem)
            cell_nome = tk.Frame(self.rows_frame, background=background, height=36)
            cell_nome.grid(row=row_index, column=1, sticky="nsew", padx=(0, 1), pady=1)
            cell_nome.grid_propagate(False)
            lbl_nome = tk.Label(
                cell_nome,
                text=employee.nome,
                background=background,
                foreground=INK,
                font=("Segoe UI", 9),
                anchor="w",
            )
            lbl_nome.place(relx=0.03, rely=0.5, anchor="w")

            # Coluna 2: Matrícula (Centralizada)
            cell_mat = tk.Frame(self.rows_frame, background=background, height=36)
            cell_mat.grid(row=row_index, column=2, sticky="nsew", padx=(0, 1), pady=1)
            cell_mat.grid_propagate(False)
            lbl_mat = tk.Label(
                cell_mat,
                text=employee.matricula,
                background=background,
                foreground=INK,
                font=("Segoe UI", 9),
            )
            lbl_mat.place(relx=0.5, rely=0.5, anchor="center")

            # Coluna 3: Função (Alinhada à esquerda)
            cell_funcao = tk.Frame(self.rows_frame, background=background, height=36)
            cell_funcao.grid(row=row_index, column=3, sticky="nsew", padx=(0, 1), pady=1)
            cell_funcao.grid_propagate(False)
            lbl_funcao = tk.Label(
                cell_funcao,
                text=employee.funcao,
                background=background,
                foreground=INK,
                font=("Segoe UI", 9),
                anchor="w",
            )
            lbl_funcao.place(relx=0.06, rely=0.5, anchor="w")

            # Vincula clique com botão direito nas células para menu de contexto
            for w in (cell_empresa, lbl_empresa, cell_nome, lbl_nome, cell_mat, lbl_mat, cell_funcao, lbl_funcao):
                w.bind("<Button-3>", lambda event, emp=employee: self._show_row_context_menu(event, emp))

            # Colunas 4+: Campos de eventos / valores monetários
            for event_offset, payroll_event in enumerate(self.events, start=4):
                key = (*employee.key, payroll_event.codigo)

                cell_event = tk.Frame(
                    self.rows_frame,
                    background=background,
                    height=36,
                )
                cell_event.grid(row=row_index, column=event_offset, sticky="nsew", padx=(0, 1), pady=1)
                cell_event.grid_propagate(False)

                entry = ttk.Entry(
                    cell_event,
                    justify="right",
                    style="Money.TEntry",
                )
                entry.insert(0, format_cents(self.values.get(key, 0)))
                entry.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.94, relheight=0.76)

                self.visible_entries.append(entry)
                self.entry_context[entry] = (employee, payroll_event.codigo)

                entry.bind("<FocusIn>", self._select_money)
                entry.bind("<FocusOut>", self._commit_money)
                entry.bind("<Return>", self._advance_entry)
                entry.bind("<Shift-Return>", self._previous_entry)
                entry.bind("<Up>", self._entry_up)
                entry.bind("<Down>", self._entry_down)
                entry.bind("<KeyRelease>", self._preview_money)

        self.after_idle(self._refresh_table_geometry)
        self.table_canvas.yview_moveto(0)
        self.update_summary()

    def _focus_employee(self, employee: Employee) -> None:
        for index, entry in enumerate(self.visible_entries):
            context_employee, _event_code = self.entry_context[entry]
            if context_employee.key == employee.key:
                self._focus_entry(index)
                return

    def _select_money(self, event: tk.Event) -> None:
        entry = event.widget
        if not isinstance(entry, ttk.Entry):
            return
        employee, event_code = self.entry_context[entry]
        event_name = next(item.nome for item in self.events if item.codigo == event_code)
        self.status_var.set(f"{employee.nome} · {event_code} — {event_name}")
        entry.after_idle(lambda: (entry.selection_range(0, tk.END), entry.icursor(tk.END)))

    def _save_entry(self, entry: ttk.Entry, format_value: bool) -> bool:
        employee, event_code = self.entry_context[entry]
        try:
            cents = parse_currency_to_cents(entry.get())
        except ValueError as exc:
            self.values[(*employee.key, event_code)] = 0
            entry.configure(style="Invalid.TEntry")
            self.status_var.set(str(exc))
            self.update_summary()
            return False

        self.values[(*employee.key, event_code)] = cents
        entry.configure(style="Money.TEntry")
        if format_value:
            entry.delete(0, tk.END)
            entry.insert(0, format_cents(cents))
        self.status_var.set("Valor registrado. Pressione Enter para avançar.")
        self.update_summary()
        return True

    def _preview_money(self, event: tk.Event) -> None:
        if event.keysym in {"Return", "Shift_L", "Shift_R", "Tab"}:
            return
        if isinstance(event.widget, ttk.Entry):
            self._save_entry(event.widget, format_value=False)

    def _commit_money(self, event: tk.Event) -> None:
        if isinstance(event.widget, ttk.Entry) and self._save_entry(event.widget, format_value=True):
            save_values(self.employees, self.events, self.values)

    def _advance_entry(self, event: tk.Event) -> str:
        entry = event.widget
        if not isinstance(entry, ttk.Entry) or not self._save_entry(entry, format_value=True):
            return "break"
        index = self.visible_entries.index(entry)
        if index + 1 < len(self.visible_entries):
            self._focus_entry(index + 1)
        else:
            self.status_var.set("Último lançamento preenchido. Confira a prévia antes de exportar.")
        return "break"

    def _previous_entry(self, event: tk.Event) -> str:
        entry = event.widget
        if not isinstance(entry, ttk.Entry) or not self._save_entry(entry, format_value=True):
            return "break"
        index = self.visible_entries.index(entry)
        if index > 0:
            self._focus_entry(index - 1)
        return "break"

    def _entry_up(self, event: tk.Event) -> str:
        entry = event.widget
        if not isinstance(entry, ttk.Entry) or not self._save_entry(entry, format_value=True):
            return "break"
        index = self.visible_entries.index(entry)
        if index >= len(self.events):
            self._focus_entry(index - len(self.events))
        return "break"

    def _entry_down(self, event: tk.Event) -> str:
        entry = event.widget
        if not isinstance(entry, ttk.Entry) or not self._save_entry(entry, format_value=True):
            return "break"
        index = self.visible_entries.index(entry)
        if index + len(self.events) < len(self.visible_entries):
            self._focus_entry(index + len(self.events))
        return "break"

    def _focus_entry(self, index: int) -> None:
        if not self.visible_entries:
            return
        entry = self.visible_entries[index]
        entry.focus_set()
        self.update_idletasks()

        # Scroll vertical
        cell = entry.master
        total_height = max(self.rows_frame.winfo_height(), 1)
        viewport_height = self.table_canvas.winfo_height()
        row_top = cell.winfo_y()
        row_bottom = row_top + cell.winfo_height()
        visible_top = self.table_canvas.yview()[0] * total_height
        visible_bottom = visible_top + viewport_height

        if row_top < visible_top:
            self.table_canvas.yview_moveto(max(0.0, row_top / total_height))
        elif row_bottom > visible_bottom:
            target = max(0.0, (row_bottom - viewport_height) / total_height)
            self.table_canvas.yview_moveto(min(1.0, target))

        # Scroll horizontal
        content_width = max(self._content_width(), 1)
        viewport_width = self.table_canvas.winfo_width()
        entry_left = cell.winfo_x()
        entry_right = entry_left + cell.winfo_width()
        visible_left = self.table_canvas.xview()[0] * content_width
        visible_right = visible_left + viewport_width

        if entry_left < visible_left:
            self._scroll_x("moveto", str(max(0.0, entry_left / content_width)))
        elif entry_right > visible_right:
            target = max(0.0, (entry_right - viewport_width) / content_width)
            self._scroll_x("moveto", str(min(1.0, target)))

    def update_summary(self) -> None:
        company_code = self.selected_company_code()
        valid_events = {event.codigo for event in self.events}
        positive_values = {
            key: value
            for key, value in self.values.items()
            if value > 0 and (not company_code or key[0] == company_code) and key[2] in valid_events
        }
        people = {(key[0], key[1]) for key in positive_values}
        lines = len(positive_values)
        total = sum(positive_values.values())
        self.people_summary_var.set(f"{len(people)} pessoa(s) com valores")
        self.lines_summary_var.set(f"{lines} evento(s) para exportar")
        self.total_summary_var.set(f"Total: {format_cents(total, include_symbol=True)}")
        self.export_button.state(("!disabled",) if lines else ("disabled",))

    def collect_launches(self) -> tuple[str, str, list[Launch]]:
        invalid_entries = [
            entry for entry in self.visible_entries if not self._save_entry(entry, format_value=True)
        ]
        if invalid_entries:
            invalid_entries[0].focus_set()
            raise ValueError(
                "Há valor(es) inválido(s) na tabela. Corrija as células destacadas antes de continuar."
            )
        calculation = normalize_calculation_code(self.calculation_var.get())
        self.calculation_var.set(calculation)
        company_code = self.selected_company_code()
        if not company_code:
            raise ValueError("Selecione uma empresa válida para exportação.")

        employee_by_key = {
            employee.key: employee for employee in self.employees if employee.empresa == company_code
        }
        event_names = {event.codigo: event.nome for event in self.events}
        launches: list[Launch] = []
        for (company, registration, event_code), cents in sorted(self.values.items()):
            if company != company_code or cents <= 0 or event_code not in event_names:
                continue
            employee = employee_by_key.get((company, registration))
            if employee is None:
                continue
            launches.append(
                Launch(
                    employee=employee,
                    event_code=event_code,
                    event_name=event_names[event_code],
                    cents=cents,
                    record=build_record(employee, calculation, event_code, cents),
                )
            )
        if not launches:
            company_name = COMPANIES.get(company_code, company_code)
            raise ValueError(
                f"Informe pelo menos um valor maior que zero para a empresa {company_code} — {company_name} antes de continuar."
            )
        return calculation, company_code, launches

    def show_preview(self) -> None:
        try:
            calculation, company_code, launches = self.collect_launches()
        except ValueError as exc:
            messagebox.showwarning("Não foi possível montar a prévia", str(exc), parent=self)
            return

        show_preview_dialog(self, calculation, launches)

    def export_txt(self) -> None:
        try:
            calculation, company_code, launches = self.collect_launches()
        except ValueError as exc:
            messagebox.showwarning("Não foi possível exportar", str(exc), parent=self)
            return

        data_dir = get_data_directory()
        path_text = filedialog.asksaveasfilename(
            parent=self,
            title=f"Salvar arquivo Modelo 35 — Empresa {company_code}",
            initialdir=str(data_dir),
            initialfile=f"r044mov_calc{calculation}_emp{company_code}_gerentes.txt",
            defaultextension=".txt",
            filetypes=(("Arquivo de texto", "*.txt"),),
        )
        if not path_text:
            return

        path = Path(path_text)
        try:
            write_txt(path, [launch.record for launch in launches])
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Não foi possível salvar o TXT",
                f"Verifique a pasta escolhida e tente novamente.\n\nDetalhe: {exc}",
                parent=self,
            )
            return

        self.status_var.set(f"TXT Empresa {company_code} exportado: {path.name} — {len(launches)} lançamento(s).")
        messagebox.showinfo(
            "TXT exportado",
            f"Arquivo da Empresa {company_code} salvo com {len(launches)} lançamento(s):\n\n{path}",
            parent=self,
        )
