import os
from loguru import logger
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET


class AndroidStringsExporter:
    def __init__(self, db_url: str, output_dir: str) -> None:
        self.engine = create_engine(db_url)
        self.output_dir = output_dir

        # Map DB language codes to Android locale resource directories
        # Extend this dict for special cases; fallback is values-<lang_code>
        self.lang_dir_map = {
            "sw": "values-sw-rTZ",   # Swahili (Tanzania)
            "rw": "values-rw-rRW",   # Kinyarwanda (Rwanda)
            # Add more mappings here, e.g. "fr": "values-fr"
        }

    def get_language_columns(self):
        """Fetch all language columns dynamically from akilimo table, skipping metadata and 'en'."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SHOW COLUMNS FROM akilimo"))
            cols = [row[0] for row in result.fetchall()]
            # Filter out non-language columns and skip 'en'
            return [c for c in cols if c not in ("lang_key", "created_at", "updated_at", "en")]

    def export(self) -> None:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM akilimo"))
            rows = result.mappings().all()
            col_names = result.keys()

            # Determine languages dynamically, excluding 'en'
            languages = self.get_language_columns()

            for lang_code in languages:
                resources = ET.Element("resources")

                for row in rows:
                    lang_key = row["lang_key"]
                    value = row.get(lang_code)

                    if not value:
                        logger.warning(f"[{lang_code}] {lang_key} missing, skipping.")
                        continue

                    # Skip array-style keys like cassava_units_of_sale[1]
                    if "[" in lang_key and "]" in lang_key:
                        logger.debug(f"Skipping array-style key: {lang_key}")
                        continue

                    string_elem = ET.SubElement(resources, "string", name=lang_key)
                    string_elem.text = value

                # Write to proper Android locale folder
                folder_name = self.lang_dir_map.get(lang_code, f"values-{lang_code}")
                lang_dir = os.path.join(self.output_dir, folder_name)
                os.makedirs(lang_dir, exist_ok=True)
                file_path = os.path.join(lang_dir, "strings.xml")
                tree = ET.ElementTree(resources)
                tree.write(file_path, encoding="utf-8", xml_declaration=True)

                logger.success(f"Exported {lang_code} translations to {file_path}")