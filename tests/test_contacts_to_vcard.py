import csv
import subprocess
import sys
from pathlib import Path

from table_of_contacts_to_vcard import (
    ParentContact,
    normalize_phone,
    parse_contacts,
    render_vcard,
    write_vcards,
)


HEADER = [
    "Vorname Kind",
    "Nachname Kind",
    "Geburtstag",
    "Strasse",
    "PLZ",
    "Ort",
    "Festnetz",
    "Vorname Mutter",
    "Nachname Mutter",
    "Vorname Vater",
    "Nachname Vater",
    "Mobil Mutter",
    "Mobil Vater",
    "Email Mutter",
    "Email Vater",
]


def write_table(path: Path, children: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write("Introductory line to skip\n")
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(children)


def child_row(name: str, **overrides: str) -> list[str]:
    values = {
        "Vorname Kind": name,
        "Nachname Kind": "Example",
        "Geburtstag": "",
        "Strasse": "Musterstraße 1",
        "PLZ": "12345",
        "Ort": "Musterstadt",
        "Festnetz": "030/12345678",
        "Vorname Mutter": "Erika",
        "Nachname Mutter": "Mustermann",
        "Vorname Vater": "Max",
        "Nachname Vater": "Mustermann",
        "Mobil Mutter": "0176/12345678",
        "Mobil Vater": "0151/23456789",
        "Email Mutter": "erika@example.com",
        "Email Vater": "max@example.com",
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
                    "Vorname Mutter": "Erika",
                    "Nachname Mutter": "Mustermann",
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


def test_omits_parent_without_parent_data(tmp_path: Path) -> None:
    table = tmp_path / "empty-parents.csv"
    write_table(
        table,
        [
            child_row(
                "Kind Eins",
                **{
                    "Vorname Mutter": "",
                    "Nachname Mutter": "",
                    "Vorname Vater": "",
                    "Nachname Vater": "",
                    "Mobil Mutter": "[ – ]",
                    "Mobil Vater": "[ – ]",
                    "Email Mutter": "?",
                    "Email Vater": "[ – ]",
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
