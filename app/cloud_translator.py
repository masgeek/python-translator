import os
import requests
from loguru import logger
from app import TRANSLATION_OVERRIDES, GOOGLE_TRANSLATOR_KEY
from app.translator import BaseTranslator


class GoogleTranslator(BaseTranslator):
    def __init__(self, source, target_langs, dry_run: bool) -> None:
        super().__init__(source, target_langs, dry_run)
        self.endpoint = "https://translation.googleapis.com/language/translate/v2"

    def _call_model(self, text: str, target_code: str) -> str:
        try:
            params = {
                "q": text,
                "target": target_code,
                "source": "en",
                "format": "text",
                "key": GOOGLE_TRANSLATOR_KEY
            }

            response = requests.post(self.endpoint, params=params)
            response.raise_for_status()
            result = response.json()
            translation = result["data"]["translations"][0]["translatedText"]

            logger.debug(f"  → {translation!r}")
            return translation
        except Exception as e:
            logger.exception(f"Google Translator error [{target_code}] on {text!r}: {e}")
            return ""
