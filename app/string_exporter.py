import os
from loguru import logger
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET


class AndroidStringsExporter:
    def __init__(self, db_url: str, output_dir: str) -> None:
        self.engine = create_engine(db_url)
        self.output_dir = output_dir

        # Map DB language codes to Android locale resource directories
        self.lang_dir_map = {
            "en": "values",          # default English
            "sw": "values-sw-rTZ",   # Swahili (Tanzania)
            "rw": "values-rw-rRW",   # Kinyarwanda (Rwanda)
        }

    def export(self, languages: list[str]) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT lang_key, en, sw, rw FROM akilimo")).fetchall()

            for lang_code in languages:
                resources = ET.Element("resources")

                # Collect arrays grouped by base name
                arrays = {}

                for row in rows:
                    lang_key, en_text, sw_text, rw_text = row

                    # Pick translation based on lang_code
                    if lang_code == "en":
                        value = en_text
                    elif lang_code == "sw":
                        value = sw_text
                    elif lang_code == "rw":
                        value = rw_text
                    else:
                        continue

                    if not value:
                        logger.warning(f"[{lang_code}] {lang_key} missing, skipping.")
                        continue

                    # Detect array keys like cassava_units_of_sale[0]
                    if "[" in lang_key and "]" in lang_key:
                        base, index = lang_key.split("[", 1)
                        arrays.setdefault(base, []).append((int(index.strip("]")), value))
                    else:
                        string_elem = ET.SubElement(resources, "string", name=lang_key)
                        string_elem.text = value

                # Write arrays as <string-array>
                for base, items in arrays.items():
                    array_elem = ET.SubElement(resources, "string-array", name=base)
                    # Sort by index to preserve order
                    for _, val in sorted(items, key=lambda x: x[0]):
                        item_elem = ET.SubElement(array_elem, "item")
                        item_elem.text = val

                # Write to proper Android locale folder
                lang_dir = os.path.join(self.output_dir, self.lang_dir_map[lang_code])
                os.makedirs(lang_dir, exist_ok=True)
                file_path = os.path.join(lang_dir, "strings.xml")
                tree = ET.ElementTree(resources)
                tree.write(file_path, encoding="utf-8", xml_declaration=True)

                logger.success(f"Exported {lang_code} translations to {file_path}")