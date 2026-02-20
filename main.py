import openpyxl
import subprocess
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from app.logging import LoggingConfig


import typer
from loguru import logger

from app import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGES, DEFAULT_PROMPT
from app.database import DatabaseTranslationSource
from app.excel import XlsxTranslationSource
from app.hf_translator import HuggingFaceTranslator
from app.cloud_translator import GoogleTranslator
from app.ollama_translator import Translator

app = typer.Typer(help="Translate Android string resources using a local Ollama model.")



def resolve_languages(languages: str | None) -> dict[str, tuple[str, str]]:
    if languages is None:
        codes = DEFAULT_LANGUAGES
    elif languages.strip().lower() == "all":
        codes = list(SUPPORTED_LANGUAGES.keys())
    else:
        codes = [l.strip() for l in languages.split(",")]
        invalid = [c for c in codes if c not in SUPPORTED_LANGUAGES]
        if invalid:
            logger.error(f"Unknown codes: {invalid}. Run 'list-languages' to see options.")
            raise typer.Exit(code=1)
    return {code: SUPPORTED_LANGUAGES[code] for code in codes}

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    Global CLI initialization.
    Runs before any subcommand.
    """
    LoggingConfig.setup(verbose=verbose, log_prefix="translate")


# ── CLI commands ──────────────────────────────────────────────────────────────
@app.command("list-languages")
def list_languages() -> None:
    """List all supported language codes."""
    typer.echo("\nSupported languages:\n")
    for code, (name, native) in SUPPORTED_LANGUAGES.items():
        marker = " ← default" if code in DEFAULT_LANGUAGES else ""
        typer.echo(f"  {code:>4}  {name:<25} ({native}){marker}")
    typer.echo()


@app.command("translate-xlsx")
def translate_xlsx(
        input_file: Path = typer.Option("translations.xlsx", "--input", "-i"),
        output_file: Path = typer.Option("translations_filled.xlsx", "--output", "-o"),
        languages: Optional[str] = typer.Option(None, "--languages", "-l", help="Codes, 'all', or omit for defaults."),
        prompt_template: str = typer.Option(DEFAULT_PROMPT, "--prompt", "-p"),
        dry_run: bool = typer.Option(False, "--dry-run", "-d"),

        verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Translate missing cells in an Excel file."""

    if not input_file.exists():
        logger.error(f"File not found: {input_file}")
        raise typer.Exit(code=1)

    target_langs = resolve_languages(languages)
    source = XlsxTranslationSource(input_file, output_file, list(target_langs.keys()))
    # translator = HuggingFaceTranslator(source, target_langs, dry_run=False)
    translator = GoogleTranslator(source, target_langs, dry_run=False)

    translator.run()


@app.command("translate-db")
def translate_db(
        db_path: str = typer.Option("translations.db", "--db", "-b", help="Path to SQLite database."),
        languages: Optional[str] = typer.Option(None, "--languages", "-l", help="Codes, 'all', or omit for defaults."),
        prompt_template: str = typer.Option(DEFAULT_PROMPT, "--prompt", "-p"),
        dry_run: bool = typer.Option(False, "--dry-run", "-d"),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Translate missing cells in a SQLite database."""
    target_langs = resolve_languages(languages)
    source = DatabaseTranslationSource(db_path, list(target_langs.keys()))
    Translator(source, target_langs, prompt_template, dry_run).run()


if __name__ == "__main__":
    app()
