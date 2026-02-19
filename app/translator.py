import openpyxl
import subprocess
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

import typer
from loguru import logger

from app import SOURCE_LANG, SOURCE_CODE, MODEL
from app.translation import TranslationSource


# ── Translator engine ─────────────────────────────────────────────────────────
class Translator:
    def __init__(
            self,
            source: TranslationSource,
            target_langs: dict[str, tuple[str, str]],
            prompt_template: str,
            dry_run: bool,
    ) -> None:
        self.source = source
        self.target_langs = target_langs
        self.prompt_template = prompt_template
        self.dry_run = dry_run

    # ── Prompt ────────────────────────────────────────────────────────────────
    def _build_prompt(self, text: str, target_code: str, target_lang: str) -> str:
        return self.prompt_template.format(
            SOURCE_LANG=SOURCE_LANG,
            SOURCE_CODE=SOURCE_CODE,
            TARGET_LANG=target_lang,
            TARGET_CODE=target_code,
            TEXT=text,
        )

    # ── Ollama call ───────────────────────────────────────────────────────────
    def _call_ollama(self, prompt: str, target_code: str, source_text: str) -> str:
        try:
            result = subprocess.run(
                ["ollama", "run", MODEL, "--json"],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8").strip()
                logger.warning(f"ollama exited {result.returncode}: {err}")
                return ""

            output = result.stdout.decode("utf-8").strip()
            translation = json.loads(output).get("response", "").strip()
            logger.debug(f"  → {translation!r}")
            return translation

        except subprocess.TimeoutExpired:
            logger.error(f"  Timeout [{target_code}]: {source_text!r}")
        except json.JSONDecodeError as e:
            logger.error(f"  Bad JSON: {e}")
        except Exception as e:
            logger.exception(f"  Unexpected error: {e}")
        return ""

    # ── Translate one cell ────────────────────────────────────────────────────
    def _translate(self, text: str, target_code: str, target_lang: str) -> str:
        prompt = self._build_prompt(text, target_code, target_lang)
        logger.debug(f"Prompt:\n{prompt}")

        if self.dry_run:
            return f"[DRY-RUN:{target_code}] {text}"

        return self._call_ollama(prompt, target_code, text)

    # ── Main run ──────────────────────────────────────────────────────────────
    def run(self) -> None:
        logger.info(f"Source backend   : {self.source.describe()}")
        logger.info(
            f"Targets ({len(self.target_langs):>2})      : {', '.join(f'{k} ({v[0]})' for k, v in self.target_langs.items())}")
        if self.dry_run:
            logger.warning("DRY-RUN — Ollama will NOT be called. One row per language only.")

        rows = self.source.load()

        total_cells = 0
        translated = 0
        skipped_filled = 0
        skipped_empty = 0
        errors = 0
        dry_run_counts: dict[str, int] = {k: 0 for k in self.target_langs}

        for idx, row in enumerate(rows, start=1):
            if not row.source_text:
                logger.warning(f"Row {idx} [{row.key}]: empty source, skipping.")
                skipped_empty += 1
                continue

            logger.info(f"Row {idx}/{len(rows)} [{row.key}]: {row.source_text!r}")

            for lang_code, (lang_name, _) in self.target_langs.items():
                total_cells += 1

                if row.translations.get(lang_code) is not None:
                    logger.debug(f"  [{lang_code}] already filled, skipping.")
                    skipped_filled += 1
                    continue

                if self.dry_run and dry_run_counts[lang_code] >= 1:
                    logger.debug(f"  [{lang_code}] dry-run limit reached.")
                    continue

                result = self._translate(row.source_text, lang_code, lang_name)

                if self.dry_run:
                    dry_run_counts[lang_code] += 1

                if result:
                    row.translations[lang_code] = result
                    translated += 1
                    logger.success(f"  [{lang_code}] ✓ {result!r}")
                else:
                    errors += 1
                    logger.error(f"  [{lang_code}] ✗ failed or empty.")

        self.source.save(rows)

        logger.info("─" * 60)
        logger.info(f"Rows processed : {len(rows)}")
        logger.info(f"Cells evaluated: {total_cells}")
        logger.success(f"Translated     : {translated}")
        logger.info(f"Already filled : {skipped_filled}")
        logger.warning(f"Skipped (empty): {skipped_empty}")
        (logger.error if errors else logger.info)(f"Errors         : {errors}")
        logger.info("─" * 60)