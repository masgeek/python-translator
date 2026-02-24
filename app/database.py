from loguru import logger
from sqlalchemy import create_engine, text
from datetime import datetime

class TranslationDBUpdater:
    def __init__(self, db_url: str, translator) -> None:
        self.engine = create_engine(db_url)
        self.g_translator = translator  # Must expose .target_langs and translate_text

    def ensure_language_columns(self) -> None:
        """Ensure all language columns in target_langs exist in akilimo table."""
        with self.engine.begin() as conn:
            # Get current columns
            result = conn.execute(text("SHOW COLUMNS FROM akilimo"))
            existing_cols = {row[0] for row in result.fetchall()}

            for lang_code in self.g_translator.target_langs.keys():
                if lang_code not in existing_cols:
                    logger.info(f"Adding missing column: {lang_code}")
                    conn.execute(
                        text(f"ALTER TABLE akilimo ADD COLUMN {lang_code} TEXT DEFAULT NULL AFTER en")
                    )

    def update_missing(self) -> None:
        """Update missing translations in akilimo, tracking in akilimo_translation_status."""
        with self.engine.begin() as conn:
            # Ensure schema is up to date
            self.ensure_language_columns()

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

                for lang_code, (lang_name, _) in self.g_translator.target_langs.items():
                    if lang_code not in col_names:
                        continue

                    current_value = row.get(lang_code)

                    # Check status table
                    status = conn.execute(
                        text("SELECT translated_at FROM akilimo_translation_status WHERE lang_key=:key AND lang_code=:code"),
                        {"key": lang_key, "code": f"{lang_code}-skip"}
                    ).fetchone()

                    if status or current_value:
                        skipped_count += 1
                        logger.debug(f"[{lang_code}] {lang_key} already translated, skipping.")
                        continue

                    # Translate
                    result_text = self.g_translator.translate_word(en_text, lang_code, lang_name, lang_key=lang_key)
                    if not result_text:
                        logger.error(f"[{lang_code}] {lang_key} ✗ failed")
                        continue

                    # Update akilimo table
                    conn.execute(
                        text(f"UPDATE akilimo SET {lang_code}=:val, updated_at=:ts WHERE lang_key=:key"),
                        {"val": result_text, "ts": datetime.now(), "key": lang_key}
                    )

                    # Insert into status table
                    # conn.execute(
                    #     text("INSERT INTO akilimo_translation_status (lang_key, lang_code, translated_at) VALUES (:key, :code, :ts)"),
                    #     {"key": lang_key, "code": lang_code, "ts": datetime.now()}
                    # )

                    updated_count += 1
                    logger.success(f"[{lang_code}] {lang_key} ✓ {result_text!r}")

            logger.info(f"Update complete: {updated_count} translations added, {skipped_count} skipped.")