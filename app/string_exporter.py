import os
from loguru import logger
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET
import re
from xml.dom import minidom


class AndroidStringsExporter:
    def __init__(self, db_url: str, output_dir: str, base_xml_path: str) -> None:
        self.engine = create_engine(db_url)
        self.output_dir = output_dir
        self.base_xml_path = base_xml_path

        # Map DB language codes to Android locale resource directories
        self.lang_dir_map = {
            "sw": "values-sw-rTZ",  # Swahili (Tanzania)
            "rw": "values-rw-rRW",  # Kinyarwanda (Rwanda)
        }

        # Load key order from original English XML
        self.key_order = self._load_key_order()

    def _load_key_order(self):
        """Parse the base English XML file to preserve key order."""
        tree = ET.parse(self.base_xml_path)
        root = tree.getroot()
        return [elem.attrib["name"] for elem in root.findall("string")]

    def get_language_columns(self):
        """Fetch all language columns dynamically from akilimo table, skipping metadata and 'en'."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM akilimo"))
            cols = [row[0] for row in result.fetchall()]
            return [c for c in cols if c not in ("lang_key", "created_at", "updated_at", "en")]

    def _sanitize_value(self, value: str) -> str:
        """
        Escape apostrophes with a single backslash for Android string resources.
        If already escaped (\' ), leave them as-is.
        """
        # Replace any ' not already preceded by a backslash
        return re.sub(r"(?<!\\)'", r"\\'", value)

    def _prettify(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string for the Element."""
        rough_string = ET.tostring(elem, encoding="utf-8")
        reparsed = minidom.parseString(rough_string)
        # Strip extra blank lines that minidom sometimes adds
        pretty = reparsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
        lines = [line for line in pretty.splitlines() if line.strip()]
        return "\n".join(lines)

    def export(self) -> None:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM akilimo"))
            rows = {row["lang_key"]: row for row in result.mappings().all()}

            languages = self.get_language_columns()

            for lang_code in languages:
                resources = ET.Element("resources")

                for key in self.key_order:
                    row = rows.get(key)
                    if not row:
                        logger.warning(f"[{lang_code}] {key} missing in DB, skipping.")
                        continue

                    value = row.get(lang_code)
                    if not value:
                        logger.warning(f"[{lang_code}] {key} missing translation, skipping.")
                        continue

                    if "[" in key and "]" in key:
                        logger.debug(f"Skipping array-style key: {key}")
                        continue

                    string_elem = ET.SubElement(resources, "string", name=key)
                    string_elem.text = self._sanitize_value(value)

                folder_name = self.lang_dir_map.get(lang_code, f"values-{lang_code}")
                lang_dir = os.path.join(self.output_dir, folder_name)
                os.makedirs(lang_dir, exist_ok=True)
                file_path = os.path.join(lang_dir, "strings.xml")

                # Pretty-print XML and ensure newline at EOF
                pretty_xml = self._prettify(resources)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pretty_xml)
                    if not pretty_xml.endswith("\n"):
                        f.write("\n")

                logger.success(f"Exported {lang_code} translations to {file_path}")
