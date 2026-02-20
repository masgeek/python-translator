import ollama
import json
from loguru import logger

from app import DEFAULT_PROMPT
from app.translator import BaseTranslator


class OllamaTranslator(BaseTranslator):
    def __init__(self, source, target_langs, prompt_template, dry_run: bool) -> None:
        super().__init__(source, target_langs, dry_run)
        self.prompt_template = prompt_template

    def _build_prompt(self, text: str, target_code: str, target_lang: str) -> str:
        return self.prompt_template.format(
            SOURCE_LANG="English",
            SOURCE_CODE="en",
            TARGET_LANG=target_lang,
            TARGET_CODE=target_code,
            TEXT=text,
        )

    def _call_model(self, target_code: str, source_text: str) -> str:
        try:
            response = ollama.chat(
                model="translategemma",
                messages=[{"role": "user", "content": DEFAULT_PROMPT}],
                stream=False,
            )
            translation = response["message"]["content"].strip()
            logger.debug(f"  → {translation!r}")
            return translation
        except Exception as e:
            logger.exception(f"  Ollama error [{target_code}] on {source_text!r}: {e}")
            return ""
