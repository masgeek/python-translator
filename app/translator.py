import re

from loguru import logger
from app import TRANSLATION_OVERRIDES
from rapidfuzz import fuzz, process


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

        # 1. Protect override phrases BEFORE translation
        protected_text, placeholder_map = self._protect_overrides(text, target_code)

        # 2. Send to model
        raw_translation = self._call_model(protected_text, target_code)

        # 3. Restore overrides AFTER translation
        final_translation = self._restore_overrides(raw_translation, placeholder_map)

        return final_translation

    def _protect_overrides(self, source_text: str, target_code: str):
        overrides = TRANSLATION_OVERRIDES.get(target_code, {})
        if not overrides:
            return source_text, {}

        protected_text = source_text
        placeholder_map = {}

        for eng, correct in overrides.items():
            pattern = re.compile(rf"\b{re.escape(eng)}\b", re.IGNORECASE)

            def replacer(match):
                original = match.group()
                placeholder = f"⟦OVR_{len(placeholder_map)}⟧"

                placeholder_map[placeholder] = (correct, original)
                return placeholder

            protected_text = pattern.sub(replacer, protected_text)

        return protected_text, placeholder_map

    def _restore_overrides(self, translated_text: str, placeholder_map: dict):
        restored = translated_text

        for placeholder, (correct, original) in placeholder_map.items():

            if original.isupper():
                replacement = correct.upper()
            elif original.istitle():
                replacement = correct.title()
            else:
                replacement = correct.lower()

            restored = restored.replace(placeholder, replacement)

        return restored

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

    def translate_word(self, source_text: str, lang_code: str, lang_name: str, lang_key) -> str:
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
