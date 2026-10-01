# Table of Contacts to vCard

**German version see below.**

Convert a parent contact CSV table to vCard 3.0 files that can be imported by Android and iOS contacts apps.


## Input Data

A single CSV file with the contacts.
Rows represent children; contacts are grouped by parent name and role, and each parent's children are listed in the vCard middle-name field.

The first CSV line is skipped by default; line 2 is used as the header.
Change or extend the skipped 1-based line numbers with `--skip-csv-lines`, for example `--skip-csv-lines 1 3`.
German national telephone numbers are converted to international `+49` format.

CSV header names are configured in the package's
`csv_parser_settings_de.toml`. This file is used by default and maps each
contact field (for example, `father_first_name`) to its CSV column name under
the `[column_names]` table.
Pass `--csv-parser-settings PATH` to use another mapping. An English mapping
is included in `csv_parser_settings_en.toml`; pass its path to parse a CSV
with English column headers. Both TOML files are included in the installed
package and wheel. If the settings file cannot be found, the converter falls
back to the built-in German column names.

The fictional example input and its generated output are available in
[`tests/fixtures/sample_contacts.csv`](tests/fixtures/sample_contacts.csv) and
[`tests/fixtures/sample_contacts.vcf`](tests/fixtures/sample_contacts.vcf).
The CSV demonstrates the expected columns and input format; the vCard shows
the combined single-file output for those contacts.

## Output data

Either a single file with all contacts (flag `--single-file`) or one file per contact (default) are generated.

The names of the children are included as middle name.

Individual contact filenames are normalized to ASCII; accented letters are
transliterated where possible (for example, `ü` becomes `u`).


## Development

The tool uses only the Python standard library.

Run the unit tests with `uv run pytest`.


# Kontakttabelle zu vCard exporter

Wandle eine CSV-Tabelle mit Elternkontakten in vCard-3.0-Dateien um, die sich
in den Kontakte-Apps von Android und iOS importieren lassen.

## Eingabedaten

Eine einzelne CSV-Datei mit den Kontaktdaten.
Jede Zeile steht für ein Kind. Die Kontakte werden nach Elternteil und Rolle
gruppiert; die Namen der Kinder werden im Mittelnamenfeld der vCard aufgeführt.

Standardmäßig wird die erste CSV-Zeile übersprungen und die zweite Zeile als
Kopfzeile verwendet. Mit `--skip-csv-lines` lassen sich weitere oder andere
Zeilen anhand ihrer 1-basierten Zeilennummer überspringen, zum Beispiel
`--skip-csv-lines 1 3`. Deutsche Telefonnummern werden in das internationale
Format mit dem Präfix `+49` umgewandelt.

Die CSV-Spaltennamen werden in der mitgelieferten Datei
`csv_parser_settings_de.toml` konfiguriert. Sie wird standardmäßig verwendet und
ordnet jedem Kontaktfeld (zum Beispiel `father_first_name`) den jeweiligen
Spaltennamen unterhalb der Tabelle `[column_names]` zu. Mit
`--csv-parser-settings PFAD` kann eine andere Zuordnung
angegeben werden. Eine englische Zuordnung ist in
`csv_parser_settings_en.toml` enthalten; damit lassen sich CSV-Dateien mit
englischen Spaltenüberschriften einlesen. Beide TOML-Dateien sind im
installierten Paket und Wheel enthalten. Wird die Einstellungsdatei nicht
gefunden, verwendet der Konverter die fest eingebauten deutschen Spaltennamen.

Eine Beispieldatei mit fiktiven Daten und die dazugehörige vCard-Ausgabe stehen
in [`tests/fixtures/sample_contacts.csv`](tests/fixtures/sample_contacts.csv)
und [`tests/fixtures/sample_contacts.vcf`](tests/fixtures/sample_contacts.vcf).
Die CSV-Datei zeigt die erwarteten Spalten und das Eingabeformat; die vCard
zeigt die zusammengefasste Ausgabe für diese Kontakte.

## Ausgabedaten

Es wird entweder eine einzelne Datei mit allen Kontakten (Flag
`--single-file`) oder standardmäßig eine Datei pro Kontakt erstellt.

Die Namen der Kinder werden als Mittelnamen aufgenommen.

Einzelne Dateinamen werden auf ASCII normalisiert; diakritische Zeichen werden
möglichst ähnlich umgeschrieben (zum Beispiel wird `ü` zu `u`).

## Entwicklung

Das Tool verwendet ausschließlich die Python-Standardbibliothek.

Führe die Unit-Tests mit `uv run pytest` aus.
