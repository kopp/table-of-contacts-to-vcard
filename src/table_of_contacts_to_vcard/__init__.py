import argparse
import csv
import io
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CSVParserSettings:
    child_first_name: str
    child_last_name: str
    birthday: str
    street: str
    postal_code: str
    city: str
    home_phone: str
    mother_first_name: str
    mother_last_name: str
    father_first_name: str
    father_last_name: str
    mother_mobile: str
    father_mobile: str
    mother_email: str
    father_email: str


DEFAULT_CSV_PARSER_SETTINGS = CSVParserSettings(
    child_first_name="Vorname Kind",
    child_last_name="Nachname Kind",
    birthday="Geburtstag",
    street="Strasse",
    postal_code="PLZ",
    city="Ort",
    home_phone="Festnetz",
    mother_first_name="Vorname Mutter",
    mother_last_name="Nachname Mutter",
    father_first_name="Vorname Vater",
    father_last_name="Nachname Vater",
    mother_mobile="Mobil Mutter",
    father_mobile="Mobil Vater",
    mother_email="Email Mutter",
    father_email="Email Vater",
)
DEFAULT_CSV_PARSER_SETTINGS_PATH = Path(__file__).with_name(
    "csv_parser_settings_de.toml"
)


def load_csv_parser_settings(
    settings_file: str | Path | None = None,
) -> CSVParserSettings:
    path = Path(settings_file) if settings_file is not None else DEFAULT_CSV_PARSER_SETTINGS_PATH
    try:
        with path.open("rb") as file:
            settings = tomllib.load(file)
    except FileNotFoundError:
        return DEFAULT_CSV_PARSER_SETTINGS

    column_names = settings.get("column_names")
    if not isinstance(column_names, dict):
        raise ValueError(
            "CSV parser settings must contain a [column_names] table."
        )

    expected_fields = DEFAULT_CSV_PARSER_SETTINGS.__dataclass_fields__
    missing_fields = expected_fields.keys() - column_names.keys()
    if missing_fields:
        raise ValueError(
            f"CSV parser settings are missing keys: {', '.join(sorted(missing_fields))}"
        )
    unknown_fields = column_names.keys() - expected_fields.keys()
    if unknown_fields:
        raise ValueError(
            f"CSV parser settings contain unknown keys: {', '.join(sorted(unknown_fields))}"
        )
    invalid_fields = [
        name for name in expected_fields if not isinstance(column_names[name], str)
    ]
    if invalid_fields:
        raise ValueError(
            f"CSV parser settings must use strings for: {', '.join(invalid_fields)}"
        )
    return CSVParserSettings(**column_names)


@dataclass
class ParentContact:
    role: str
    first_name: str
    last_name: str
    children: list[str] = field(default_factory=list)
    phones: list[tuple[str, str]] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    address: tuple[str, str, str] = ("", "", "")

    @property
    def middle_name(self) -> str:
        return f"{self.role} von {' und '.join(self.children)}".strip()


def clean_value(value: str | None) -> str:
    value = (value or "").strip()
    value = "".join(char for char in value if unicodedata.category(char) != "Cf")
    if not value:
        return ""
    marker = value.strip().strip("[]").strip()
    if marker == "?" or all(char.isspace() or unicodedata.category(char) == "Pd" or char in "−–—" for char in marker):
        return ""
    return value


def normalize_phone(value: str | None) -> str:
    value = clean_value(value)
    if not value:
        return ""

    digits = "".join(str(unicodedata.digit(char)) for char in value if char.isdigit())
    if not digits:
        return ""

    if value.lstrip().startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if digits.startswith("49"):
        return f"+{digits}"
    if digits.startswith("0"):
        digits = digits[1:]
    return f"+49{digits}"


def _add_unique(values: list, value) -> None:
    if value and value not in values:
        values.append(value)


def _validate_csv_headers(
    provided_headers: list[str], settings: CSVParserSettings
) -> None:
    expected_headers = list(vars(settings).values())
    normalized_headers = [header.strip() for header in provided_headers]
    expected_set = set(expected_headers)
    provided_set = set(normalized_headers)
    missing = sorted(expected_set - provided_set)
    unexpected = sorted(provided_set - expected_set)
    if missing or unexpected:
        raise ValueError(
            "CSV columns do not match the configured parser settings.\n"
            f"Expected columns: {', '.join(expected_headers)}\n"
            f"Provided columns: {', '.join(normalized_headers)}\n"
            f"Missing columns: {', '.join(missing) or '(none)'}\n"
            f"Unexpected columns: {', '.join(unexpected) or '(none)'}\n"
            "Use --csv-parser-settings to select a different column mapping."
        )


def parse_contacts(
    input_table: str | Path,
    skip_csv_lines: list[int] | None = None,
    csv_parser_settings: str | Path | CSVParserSettings | None = None,
) -> list[ParentContact]:
    settings = (
        csv_parser_settings
        if isinstance(csv_parser_settings, CSVParserSettings)
        else load_csv_parser_settings(csv_parser_settings)
    )
    skipped = set([1] if skip_csv_lines is None else skip_csv_lines)
    if any(line < 1 for line in skipped):
        raise ValueError("CSV line numbers to skip must be greater than zero")

    with Path(input_table).open(encoding="utf-8-sig", newline="") as file:
        content = "".join(line for number, line in enumerate(file, start=1) if number not in skipped)

    contacts: dict[tuple[str, str, str], ParentContact] = {}
    reader = csv.DictReader(io.StringIO(content, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV file does not contain a header")
    _validate_csv_headers(reader.fieldnames, settings)

    for row in reader:
        row = {(key or "").strip(): value for key, value in row.items() if key is not None}
        child_name = clean_value(row.get(settings.child_first_name))
        street = clean_value(row.get(settings.street))
        postal_code = clean_value(row.get(settings.postal_code))
        city = clean_value(row.get(settings.city))

        for role, label, first_column, last_column, phone_column, email_column in (
            (
                "Mama",
                "mother",
                settings.mother_first_name,
                settings.mother_last_name,
                settings.mother_mobile,
                settings.mother_email,
            ),
            (
                "Papa",
                "father",
                settings.father_first_name,
                settings.father_last_name,
                settings.father_mobile,
                settings.father_email,
            ),
        ):
            first_name = clean_value(row.get(first_column))
            last_name = clean_value(row.get(last_column))
            phone = normalize_phone(row.get(phone_column))
            email = clean_value(row.get(email_column))
            if not any((first_name, last_name, phone, email)):
                continue

            identity = (first_name.casefold(), last_name.casefold())
            if not any(identity):
                identity = (phone, "") if phone else ("", email.casefold())
            key = (label, *identity)
            contact = contacts.get(key)
            if contact is None:
                contact = ParentContact(role, first_name, last_name)
                contacts[key] = contact
            if not contact.first_name:
                contact.first_name = first_name
            if not contact.last_name:
                contact.last_name = last_name

            _add_unique(contact.children, child_name)
            _add_unique(contact.phones, ("CELL", phone))
            _add_unique(
                contact.phones,
                ("HOME", normalize_phone(row.get(settings.home_phone))),
            )
            _add_unique(contact.emails, email)
            if not any(contact.address):
                contact.address = (street, postal_code, city)

    return list(contacts.values())


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _fold_line(line: str) -> str:
    chunks: list[str] = []
    current = ""
    for char in line:
        candidate = current + char
        if len(candidate.encode("utf-8")) > (75 if not chunks else 74):
            chunks.append(current)
            current = " " + char
        else:
            current = candidate
    chunks.append(current)
    return "\r\n".join(chunks)


def _filename_slug(value: str) -> str:
    transliteration = str.maketrans(
        {
            "ß": "ss",
            "ẞ": "SS",
            "æ": "ae",
            "Æ": "AE",
            "œ": "oe",
            "Œ": "OE",
            "ø": "o",
            "Ø": "O",
            "ł": "l",
            "Ł": "L",
            "đ": "d",
            "Đ": "D",
            "ð": "d",
            "Ð": "D",
            "þ": "th",
            "Þ": "Th",
        }
    )
    decomposed = unicodedata.normalize("NFKD", value.translate(transliteration))
    ascii_name = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", ascii_name).strip(".-")


def render_vcard(contact: ParentContact) -> str:
    given = _escape(contact.first_name)
    middle = _escape(contact.middle_name)
    family = _escape(contact.last_name)
    display_name = " ".join(part for part in (given, middle, family) if part)
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{family};{given};{middle};;",
        f"FN:{display_name}",
    ]
    for phone_type, phone in contact.phones:
        if phone:
            lines.append(f"TEL;TYPE={phone_type}:{phone}")
    for email in contact.emails:
        lines.append(f"EMAIL;TYPE=HOME:{_escape(email)}")
    street, postal_code, city = contact.address
    if any(contact.address):
        lines.append("ADR;TYPE=HOME:;;" f"{_escape(street)};{_escape(city)};;{_escape(postal_code)};Germany")
    lines.extend(("END:VCARD", ""))
    return "\r\n".join(_fold_line(line) for line in lines)


def write_vcards(contacts: list[ParentContact], output: str | Path, single_file: bool = False) -> list[Path]:
    output_path = Path(output)
    if single_file:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "".join(render_vcard(contact) for contact in contacts),
            encoding="utf-8",
            newline="",
        )
        return [output_path]

    output_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used_names: set[str] = set()
    for contact in contacts:
        name = " ".join(part for part in (contact.first_name, contact.last_name) if part)
        slug = _filename_slug(name)
        slug = slug or "contact"
        base_name = slug
        filename = f"{base_name}.vcf"
        suffix = 2
        while filename.casefold() in used_names:
            filename = f"{base_name}-{suffix}.vcf"
            suffix += 1
        used_names.add(filename.casefold())
        path = output_path / filename
        path.write_text(render_vcard(contact), encoding="utf-8", newline="")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a German parent contact CSV table to vCard files.")
    parser.add_argument("--input-table", required=True, help="Input CSV file")
    parser.add_argument(
        "--output",
        required=True,
        help="Output .vcf file with --single-file, otherwise an output directory",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Write all parent contacts to one vCard file",
    )
    parser.add_argument(
        "--skip-csv-lines",
        nargs="+",
        type=int,
        default=[1],
        help="1-based CSV document line numbers to skip (default: 1)",
    )
    parser.add_argument(
        "--csv-parser-settings",
        default=str(DEFAULT_CSV_PARSER_SETTINGS_PATH),
        help=(
            "TOML file mapping contact fields to CSV column names "
            f"(default: {DEFAULT_CSV_PARSER_SETTINGS_PATH.name})"
        ),
    )
    args = parser.parse_args()

    try:
        contacts = parse_contacts(
            args.input_table, args.skip_csv_lines, args.csv_parser_settings
        )
        write_vcards(contacts, args.output, args.single_file)
    except (OSError, ValueError, csv.Error) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
