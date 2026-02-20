import re

from loguru import logger
from app import TRANSLATION_OVERRIDES


class BaseTranslator:
    def __init__(self, source, target_langs, dry_run: bool) -> None:
        self.source = source
        self.target_langs = target_langs
        self.dry_run = dry_run

    def _call_model(self, text: str, target_code: str) -> str:
        """
        Abstract method: must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _call_model")

    def _translate(self, text: str, target_code: str, target_lang: str, lang_key: str) -> str:

        logger.debug(f"Translating to {target_lang} [{target_code}] and key--> {lang_key}")

        if self.dry_run:
            return f"[DRY-RUN:{target_code}] {text}"

        raw_translation = self._call_model(text, target_code)
        final_translation = self._apply_overrides(text, raw_translation, target_code)
        return final_translation

    def is_array_key(self, key: str) -> bool:
        if not key:
            return False

        start = key.find("[")
        end = key.find("]")

        if start == -1 or end == -1:
            return False

        if start < end and end - start > 1:
            return True

        return False

    def _apply_overrides(self, source_text: str, translated_text: str, target_code: str) -> str:
        overrides = TRANSLATION_OVERRIDES.get(target_code, {})
        words = translated_text.split()
        corrected_words = []

        for w in words:
            lw = w.lower().strip("!?.,")
            for eng, correct in overrides.items():
                if eng.lower() in source_text.lower() and (lw == eng.lower() or "mgongo" in lw):
                    corrected_words.append(correct)
                    break
            else:
                corrected_words.append(w)

        return " ".join(corrected_words)

    def translate_text(self, source_text: str, lang_code: str, lang_name: str, lang_key) -> str:
        """
        Public method for external callers (e.g., DB updater).
        """
        if self.is_array_key(lang_key):
            logger.error(f"Skipping translation for array key: {lang_key}")
            return ""

        return self._translate(source_text, lang_code, lang_name, lang_key)

    def run(self) -> None:
        rows = self.source.load()
        for idx, row in enumerate(rows, start=1):
            if not row.source_text:
                logger.warning(f"Row {idx} [{row.key}]: empty source, skipping.")
                continue

            logger.info(f"Row {idx}/{len(rows)} [{row.key}]: {row.source_text!r}")

            for lang_code, (lang_name, _) in self.target_langs.items():
                if row.translations.get(lang_code) is not None:
                    logger.debug(f"  [{lang_code}] already filled, skipping.")
                    continue

                result = self._translate(row.source_text, lang_code, lang_name, lang_key=row.key)
                if result:
                    row.translations[lang_code] = result
                    logger.success(f"  [{lang_code}] ✓ {result!r}")
                else:
                    logger.error(f"  [{lang_code}] ✗ failed or empty.")

        self.source.save(rows)
