from loguru import logger
from sqlalchemy import create_engine, text

class TranslationDBUpdater:
    def __init__(self, db_url: str,translator) -> None:
        self.engine = create_engine(db_url)
        self.translator = translator

    def update_missing(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT lang_key, en, sw, rw FROM akilimo")).fetchall()
            updated_count = 0
            skipped_count = 0

            for row in rows:
                lang_key, en_text, sw_text, rw_text = row

                if not en_text:
                    logger.warning(f"[{lang_key}] has no English source, skipping.")
                    continue

                for lang_code, (lang_name, _) in self.translator.target_langs.items():
                    current_value = sw_text if lang_code == "sw" else rw_text if lang_code == "rw" else None

                    if not current_value:
                        result = self.translator.translate_text(en_text, lang_code, lang_name)
                        if result:
                            conn.execute(
                                text(f"UPDATE akilimo SET {lang_code}=:val WHERE lang_key=:key"),
                                {"val": result, "key": lang_key},
                            )
                            updated_count += 1
                            logger.success(f"[{lang_code}] {lang_key} ✓ {result!r}")
                        else:
                            logger.error(f"[{lang_code}] {lang_key} ✗ failed")
                    else:
                        skipped_count += 1
                        logger.debug(f"[{lang_code}] {lang_key} already filled, skipping.")

            conn.commit()
            logger.info(f"Update complete: {updated_count} translations added, {skipped_count} skipped.")