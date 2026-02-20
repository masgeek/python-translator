from loguru import logger
from sqlalchemy import create_engine, text
from datetime import datetime

class TranslationDBUpdater:
    def __init__(self, db_url: str, translator) -> None:
        self.engine = create_engine(db_url)
        self.translator = translator  # Must expose .target_langs and translate_text

    def update_missing(self) -> None:
        with self.engine.begin() as conn:
            # Fetch all rows dynamically
            result = conn.execute(text("SELECT * FROM akilimo"))
            rows = result.mappings().all()
            col_names = result.keys()

            updated_count = 0
            skipped_count = 0

            for row in rows:
                lang_key = row["lang_key"]
                en_text = row["en"]

                if not en_text:
                    logger.warning(f"[{lang_key}] has no English source, skipping.")
                    continue

                for lang_code, (lang_name, _) in self.translator.target_langs.items():
                    # Skip if column doesn’t exist yet
                    if lang_code not in col_names:
                        logger.debug(f"[{lang_code}] column not present, skipping.")
                        continue

                    current_value = row[lang_code]

                    # Check status table
                    status = conn.execute(
                        text("SELECT translated_at FROM akilimo_translation_status WHERE lang_key=:key AND lang_code=:code"),
                        {"key": lang_key, "code": lang_code}
                    ).fetchone()

                    if status or current_value:
                        skipped_count += 1
                        logger.debug(f"[{lang_code}] {lang_key} already translated, skipping.")
                        continue

                    # Translate
                    result = self.translator.translate_text(en_text, lang_code, lang_name, lang_key=lang_key)
                    if not result:
                        logger.error(f"[{lang_code}] {lang_key} ✗ failed")
                        continue

                    # Update akilimo table
                    conn.execute(
                        text(f"UPDATE akilimo SET {lang_code}=:val, updated_at=:ts WHERE lang_key=:key"),
                        {"val": result, "ts": datetime.now(), "key": lang_key}
                    )

                    # Insert into status table
                    conn.execute(
                        text("INSERT INTO akilimo_translation_status (lang_key, lang_code, translated_at) VALUES (:key, :code, :ts)"),
                        {"key": lang_key, "code": lang_code, "ts": datetime.now()}
                    )

                    updated_count += 1
                    logger.success(f"[{lang_code}] {lang_key} ✓ {result!r}")

            logger.info(f"Update complete: {updated_count} translations added, {skipped_count} skipped.")