import csv
import subprocess
import sys
from pathlib import Path

import pytest

from table_of_contacts_to_vcard import (
    DEFAULT_CSV_PARSER_SETTINGS,
    ParentContact,
    load_csv_parser_settings,
    normalize_phone,
    parse_contacts,
    render_vcard,
    write_vcards,
)


HEADER = [
    DEFAULT_CSV_PARSER_SETTINGS.child_first_name,
    DEFAULT_CSV_PARSER_SETTINGS.child_last_name,
    DEFAULT_CSV_PARSER_SETTINGS.birthday,
    DEFAULT_CSV_PARSER_SETTINGS.street,
    DEFAULT_CSV_PARSER_SETTINGS.postal_code,
    DEFAULT_CSV_PARSER_SETTINGS.city,
    DEFAULT_CSV_PARSER_SETTINGS.home_phone,
    DEFAULT_CSV_PARSER_SETTINGS.mother_first_name,
    DEFAULT_CSV_PARSER_SETTINGS.mother_last_name,
    DEFAULT_CSV_PARSER_SETTINGS.father_first_name,
    DEFAULT_CSV_PARSER_SETTINGS.father_last_name,
    DEFAULT_CSV_PARSER_SETTINGS.mother_mobile,
    DEFAULT_CSV_PARSER_SETTINGS.father_mobile,
    DEFAULT_CSV_PARSER_SETTINGS.mother_email,
    DEFAULT_CSV_PARSER_SETTINGS.father_email,
]


def write_table(path: Path, children: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write("Introductory line to skip\n")
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(children)


def child_row(name: str, **overrides: str) -> list[str]:
    values = {
        DEFAULT_CSV_PARSER_SETTINGS.child_first_name: name,
        DEFAULT_CSV_PARSER_SETTINGS.child_last_name: "Example",
        DEFAULT_CSV_PARSER_SETTINGS.birthday: "",
        DEFAULT_CSV_PARSER_SETTINGS.street: "Musterstraße 1",
        DEFAULT_CSV_PARSER_SETTINGS.postal_code: "12345",
        DEFAULT_CSV_PARSER_SETTINGS.city: "Musterstadt",
        DEFAULT_CSV_PARSER_SETTINGS.home_phone: "030/12345678",
        DEFAULT_CSV_PARSER_SETTINGS.mother_first_name: "Erika",
        DEFAULT_CSV_PARSER_SETTINGS.mother_last_name: "Mustermann",
        DEFAULT_CSV_PARSER_SETTINGS.father_first_name: "Max",
        DEFAULT_CSV_PARSER_SETTINGS.father_last_name: "Mustermann",
        DEFAULT_CSV_PARSER_SETTINGS.mother_mobile: "0176/12345678",
        DEFAULT_CSV_PARSER_SETTINGS.father_mobile: "0151/23456789",
        DEFAULT_CSV_PARSER_SETTINGS.mother_email: "erika@example.com",
        DEFAULT_CSV_PARSER_SETTINGS.father_email: "max@example.com",
    }
    values.update(overrides)
    return [values[column] for column in HEADER]


def test_parses_single_csv_row_and_maps_parent_fields(tmp_path: Path) -> None:
    table = tmp_path / "contacts.csv"
    write_table(
        table,
        [
            child_row(
                "Kind Eins",
                **{
                    DEFAULT_CSV_PARSER_SETTINGS.mother_first_name: "Erika",
                    DEFAULT_CSV_PARSER_SETTINGS.mother_last_name: "Mustermann",
                },
            )
        ],
    )

    contacts = parse_contacts(table)
    mother = next(contact for contact in contacts if contact.role == "Mama")
    vcard = render_vcard(mother)

    assert mother.middle_name == "Mama von Kind Eins"
    assert "N:Mustermann;Erika;Mama von Kind Eins;;" in vcard
    assert "TEL;TYPE=CELL:+4917612345678" in vcard
    assert "TEL;TYPE=HOME:+493012345678" in vcard
    assert "EMAIL;TYPE=HOME:erika@example.com" in vcard
    assert "ADR;TYPE=HOME:;;Musterstraße 1;Musterstadt;;12345;Germany" in vcard


def test_groups_children_of_same_parents_into_one_contact(tmp_path: Path) -> None:
    table = tmp_path / "siblings.csv"
    write_table(
        table,
        [child_row("Kind Eins"), child_row("Kind Zwei"), child_row("Kind Drei")],
    )

    contacts = parse_contacts(table)
    mothers = [contact for contact in contacts if contact.role == "Mama"]

    assert len(mothers) == 1
    assert mothers[0].middle_name == "Mama von Kind Eins und Kind Zwei und Kind Drei"
    assert render_vcard(mothers[0]).count("BEGIN:VCARD") == 1


def test_sample_csv_has_combined_contact_for_erika() -> None:
    sample = Path(__file__).parent / "fixtures" / "sample_contacts.csv"

    contacts = parse_contacts(sample)
    erika = next(
        contact
        for contact in contacts
        if contact.first_name == "Erika" and contact.role == "Mama"
    )

    assert erika.middle_name == "Mama von Kind Eins und Kind Zwei"


def test_sample_csv_generates_expected_single_vcard_file(tmp_path: Path) -> None:
    repository = Path(__file__).parents[1]
    sample = Path(__file__).parent / "fixtures" / "sample_contacts.csv"
    expected = Path(__file__).parent / "fixtures" / "sample_contacts.vcf"
    output = tmp_path / "all-contacts.vcf"

    subprocess.run(
        [
            sys.executable,
            str(repository / "src" / "table_of_contacts_to_vcard" / "__init__.py"),
            "--input-table",
            str(sample),
            "--output",
            str(output),
            "--single-file",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.read_bytes() == expected.read_bytes()
    assert output.read_text(encoding="utf-8").count("BEGIN:VCARD") == 2


def test_english_csv_parser_settings(tmp_path: Path) -> None:
    settings_path = (
        Path(__file__).parents[1]
        / "src"
        / "table_of_contacts_to_vcard"
        / "csv_parser_settings_en.toml"
    )
    settings = load_csv_parser_settings(settings_path)
    table = tmp_path / "english-contacts.csv"
    sample_values = {
        "child_first_name": "Child One",
        "street": "Sample Street 1",
        "postal_code": "12345",
        "city": "Sampletown",
        "home_phone": "030/12345678",
        "mother_first_name": "Erika",
        "mother_last_name": "Mustermann",
        "mother_mobile": "0176/12345678",
        "mother_email": "erika@example.com",
    }
    with table.open("w", encoding="utf-8", newline="") as file:
        file.write("Fictional sample data\n")
        writer = csv.writer(file)
        writer.writerow(vars(settings).values())
        writer.writerow(
            [sample_values.get(name, "") for name in vars(settings)]
        )

    contacts = parse_contacts(table, csv_parser_settings=settings)
    mother = next(contact for contact in contacts if contact.role == "Mama")

    assert mother.middle_name == "Mama von Child One"
    assert mother.phones == [
        ("CELL", "+4917612345678"),
        ("HOME", "+493012345678"),
    ]
    output = tmp_path / "english-contacts.vcf"
    repository = Path(__file__).parents[1]
    subprocess.run(
        [
            sys.executable,
            str(repository / "src" / "table_of_contacts_to_vcard" / "__init__.py"),
            "--input-table",
            str(table),
            "--output",
            str(output),
            "--single-file",
            "--csv-parser-settings",
            str(settings_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "N:Mustermann;Erika;Mama von Child One;;" in output.read_text(
        encoding="utf-8"
    )


def test_missing_csv_parser_settings_falls_back_to_default_columns(
    tmp_path: Path,
) -> None:
    settings = load_csv_parser_settings(tmp_path / "missing-settings.toml")
    assert settings == DEFAULT_CSV_PARSER_SETTINGS


def test_csv_parser_settings_requires_column_names_table(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings-without-table.toml"
    settings_path.write_text(
        'father_first_name = "Father first name"\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match=r"must contain a \[column_names\] table"):
        load_csv_parser_settings(settings_path)


def test_csv_header_error_lists_expected_provided_and_delta(tmp_path: Path) -> None:
    table = tmp_path / "wrong-columns.csv"
    with table.open("w", encoding="utf-8", newline="") as file:
        file.write("Introductory line to skip\n")
        writer = csv.writer(file)
        writer.writerow([*HEADER[:-1], "Unexpected column"])

    with pytest.raises(ValueError) as error:
        parse_contacts(table)

    message = str(error.value)
    assert f"Expected columns: {', '.join(HEADER)}" in message
    assert (
        f"Provided columns: {', '.join([*HEADER[:-1], 'Unexpected column'])}"
        in message
    )
    assert "Missing columns: Email Vater" in message
    assert "Unexpected columns: Unexpected column" in message
    assert "--csv-parser-settings" in message


def test_omits_parent_without_parent_data(tmp_path: Path) -> None:
    table = tmp_path / "empty-parents.csv"
    write_table(
        table,
        [
            child_row(
                "Kind Eins",
                **{
                    DEFAULT_CSV_PARSER_SETTINGS.mother_first_name: "",
                    DEFAULT_CSV_PARSER_SETTINGS.mother_last_name: "",
                    DEFAULT_CSV_PARSER_SETTINGS.father_first_name: "",
                    DEFAULT_CSV_PARSER_SETTINGS.father_last_name: "",
                    DEFAULT_CSV_PARSER_SETTINGS.mother_mobile: "[ – ]",
                    DEFAULT_CSV_PARSER_SETTINGS.father_mobile: "[ – ]",
                    DEFAULT_CSV_PARSER_SETTINGS.mother_email: "?",
                    DEFAULT_CSV_PARSER_SETTINGS.father_email: "[ – ]",
                },
            )
        ],
    )

    assert parse_contacts(table) == []


def test_phone_cleanup_and_vcard_file_modes(tmp_path: Path) -> None:
    assert normalize_phone("‭0176/12345678‬") == "+4917612345678"
    assert normalize_phone("0049 176 1234567") == "+491761234567"
    assert normalize_phone("[ – ]") == ""

    contacts = [
        ParentContact("Mama", "Erika", "Mustermann", children=["Kind Eins"])
    ]
    single_file = tmp_path / "all.vcf"
    write_vcards(contacts, single_file, single_file=True)
    assert single_file.read_text(encoding="utf-8").count("BEGIN:VCARD") == 1

    output_dir = tmp_path / "contacts"
    paths = write_vcards(contacts, output_dir)
    assert len(paths) == 1
    assert paths[0].name == "Erika-Mustermann.vcf"
