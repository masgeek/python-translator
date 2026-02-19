import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

import typer
from loguru import logger

from app.translation import TranslationSource, TranslationRow


# ── Database backend ──────────────────────────────────────────────────────────
class DatabaseTranslationSource(TranslationSource):
    """
    SQLite backend (swap connection string / driver for Postgres, MySQL, etc.).

    Expected schema:
        CREATE TABLE translations (
            key         TEXT PRIMARY KEY,
            source_text TEXT NOT NULL,
            rw          TEXT,
            sw          TEXT,
            fr          TEXT,
            -- ... one column per language code
        );
    """

    def __init__(self, db_path: str, lang_codes: list[str]) -> None:
        self.db_path = db_path
        self.lang_codes = lang_codes
        self._rows_cache: list[TranslationRow] = []

    def describe(self) -> str:
        return f"SQLite {self.db_path}"

    def _connect(self):
        import sqlite3
        return sqlite3.connect(self.db_path)

    def load(self) -> list[TranslationRow]:
        logger.info(f"Connecting to database: {self.db_path}")
        lang_cols = ", ".join(self.lang_codes)
        query = f"SELECT key, source_text, {lang_cols} FROM translations"

        with self._connect() as conn:
            cursor = conn.execute(query)
            col_names = [d[0] for d in cursor.description]
            raw_rows = cursor.fetchall()

        logger.info(f"Loaded {len(raw_rows)} rows from database.")
        rows: list[TranslationRow] = []
        for raw in raw_rows:
            record = dict(zip(col_names, raw))
            translations = {code: record.get(code) for code in self.lang_codes}
            rows.append(TranslationRow(
                key=record["key"],
                source_text=record["source_text"],
                translations=translations,
            ))

        self._rows_cache = rows
        return rows

    def save(self, rows: list[TranslationRow]) -> None:
        with self._connect() as conn:
            for row in rows:
                set_clause = ", ".join(f"{code} = ?" for code in self.lang_codes)
                values = [row.translations.get(code) for code in self.lang_codes]
                conn.execute(
                    f"UPDATE translations SET {set_clause} WHERE key = ?",
                    [*values, row.key],
                )
            conn.commit()
        logger.success(f"Database updated — {len(rows)} rows written.")

