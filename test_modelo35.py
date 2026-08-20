import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from export_gerentes import (
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
    load_values,
    normalize_calculation_code,
    normalize_company,
    normalize_event_code,
    normalize_registration,
    parse_currency_to_cents,
    save_employees,
    save_events,
    save_values,
    write_txt,
)


class CurrencyTests(unittest.TestCase):
    def test_brazilian_currency(self):
        self.assertEqual(parse_currency_to_cents("R$ 1.250,50"), 125050)
        self.assertEqual(format_cents(125050), "1.250,50")

    def test_negative_value_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_currency_to_cents("-10,00")

    def test_malformed_and_fractional_cent_values_are_rejected(self):
        for value in ("12.34.56", "1,234", "0,005", "1E3", "NaN", "Infinity"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_currency_to_cents(value)

    def test_layout_value_limit(self):
        self.assertEqual(parse_currency_to_cents("999.999.999,99"), 99_999_999_999)
        with self.assertRaises(ValueError):
            parse_currency_to_cents("1.000.000.000,00")


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.employee = Employee(
            empresa="0018", nome="GERENTE TESTE", matricula="000001234", funcao="Gerente"
        )

    def test_record_has_exact_layout(self):
        record = build_record(self.employee, "407", "816", 125050)
        self.assertEqual(len(record), 62)
        self.assertEqual(record[0:2], "01")
        self.assertEqual(record[2:6], "0018")
        self.assertEqual(record[6:7], "1")
        self.assertEqual(record[7:16], "000001234")
        self.assertEqual(record[16:21], "00407")
        self.assertEqual(record[21:24], "019")
        self.assertEqual(record[24:28], "0816")
        self.assertEqual(record[28:37], "000000000")
        self.assertEqual(record[37:39], "01")
        self.assertEqual(record[39:50], "00000000000")
        self.assertEqual(record[50:61], "00000125050")
        self.assertEqual(record[61], "I")

    def test_txt_uses_one_record_per_line(self):
        record = build_record(self.employee, "00407", "0239", 8590)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saida.txt"
            write_txt(path, [record, record])
            data = path.read_bytes()
        self.assertEqual(data, (record + "\r\n" + record + "\r\n").encode("ascii"))

    def test_calculation_is_zero_padded(self):
        self.assertEqual(normalize_calculation_code("407"), "00407")

    def test_calculation_rejects_non_digits(self):
        with self.assertRaises(ValueError):
            normalize_calculation_code("calc407")
        with self.assertRaises(ValueError):
            normalize_calculation_code("４０７")

    def test_company_is_part_of_each_record(self):
        employee = Employee("0019", "OUTRA GERENTE", "000001234", "Gerente")
        record = build_record(employee, "00407", "1102", 30000)
        self.assertEqual(record[2:6], "0019")
        self.assertEqual(record[24:28], "1102")

    def test_each_positive_event_builds_its_own_record(self):
        records = [
            build_record(self.employee, "00407", event_code, cents)
            for event_code, cents in (("0816", 1000), ("0239", 2500), ("1102", 3000))
        ]
        self.assertEqual(len(records), 3)
        self.assertEqual([record[24:28] for record in records], ["0816", "0239", "1102"])

    def test_unknown_company_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_company("20")
        employee = Employee("0020", "TESTE", "000001234", "Gerente")
        with self.assertRaises(ValueError):
            build_record(employee, "00407", "0816", 1000)


class EmployeeFileTests(unittest.TestCase):
    def test_company_and_registration_are_zero_padded(self):
        content = "empresa;nome;matricula;funcao\n18;MARIA;1234;Gerente\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colaboradores.csv"
            path.write_text(content, encoding="utf-8")
            employee = load_employees(path)[0]
        self.assertEqual(employee.empresa, "0018")
        self.assertEqual(employee.matricula, "000001234")

    def test_legacy_branch_column_is_accepted_and_removed_when_saved(self):
        content = "filial;empresa;nome;matricula;funcao\n001;18;MARIA;1234;Gerente\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colaboradores.csv"
            path.write_text(content, encoding="utf-8")
            self.assertTrue(employee_file_has_legacy_branch(path))
            employees = load_employees(path)
            save_employees(employees, path)
            header = path.read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertEqual(header, "empresa;nome;matricula;funcao")

    def test_employee_created_in_app_persists(self):
        employee = Employee("0019", "JOSÉ", "000001234", "Subgerente")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colaboradores.csv"
            save_employees([employee], path)
            loaded = load_employees(path)
        self.assertEqual(loaded, [employee])

    def test_cp1252_csv_is_supported(self):
        content = "empresa;nome;matricula;funcao\n18;JOSÉ;1234;Gerente\n".encode("cp1252")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colaboradores.csv"
            path.write_bytes(content)
            employee = load_employees(path)[0]
        self.assertEqual(employee.nome, "JOSÉ")

    def test_non_numeric_registration_is_rejected(self):
        content = "empresa;nome;matricula;funcao\n18;MARIA;12-34;Gerente\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colaboradores.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(EmployeeFileError):
                load_employees(path)


class EventFileTests(unittest.TestCase):
    def test_missing_event_file_returns_four_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            events = load_events(Path(directory) / "eventos.csv")
        self.assertEqual(events, list(DEFAULT_EVENTS))

    def test_custom_event_is_persisted_after_defaults(self):
        custom = PayrollEvent("1234", "Bônus Especial")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eventos.csv"
            save_events([*DEFAULT_EVENTS, custom], path)
            loaded = load_events(path)
        self.assertEqual(loaded[-1], custom)
        self.assertEqual(loaded[:4], list(DEFAULT_EVENTS))

    def test_event_code_is_zero_padded(self):
        self.assertEqual(normalize_event_code("37"), "0037")

    def test_duplicate_event_is_rejected(self):
        content = "codigo;nome\n1234;A\n1234;B\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eventos.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(EventFileError):
                load_events(path)


class StorageDirectoryTests(unittest.TestCase):
    def test_frozen_storage_uses_appdata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.frozen", True, create=True), patch.dict(os.environ, {"APPDATA": tmp}):
                data_dir = get_data_directory()
                self.assertEqual(data_dir, Path(tmp) / "ExportGerentes")
                self.assertTrue(data_dir.exists())


class ValuesFileTests(unittest.TestCase):
    def setUp(self):
        self.employees = [
            Employee("0018", "GERENTE TESTE", "000001234", "Gerente"),
            Employee("0019", "MONTADOR TESTE", "000005678", "Montador"),
        ]
        self.events = list(DEFAULT_EVENTS)

    def test_save_and_load_values_persists_correctly(self):
        values = {
            ("0018", "000001234", "0816"): 150000,
            ("0018", "000001234", "0239"): 25050,
            ("0019", "000005678", "1074"): 30000,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valores.csv"
            save_values(self.employees, self.events, values, path)
            loaded = load_values(self.employees, self.events, path)

        self.assertEqual(loaded[("0018", "000001234", "0816")], 150000)
        self.assertEqual(loaded[("0018", "000001234", "0239")], 25050)
        self.assertEqual(loaded[("0019", "000005678", "1074")], 30000)
        self.assertNotIn(("0019", "000005678", "0816"), loaded)

    def test_missing_values_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nao_existe.csv"
            loaded = load_values(self.employees, self.events, path)
        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
