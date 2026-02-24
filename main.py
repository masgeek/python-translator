from os import getenv
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from loguru import logger

from app import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGES, DEFAULT_PROMPT
from app.cloud_translator import GoogleTranslator
from app.database import TranslationDBUpdater
from app.excel import XlsxTranslationSource
from app.logging import LoggingConfig
from app.string_exporter import AndroidStringsExporter

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
    LoggingConfig.setup(verbose=True, log_prefix="translate")


# ── CLI commands ──────────────────────────────────────────────────────────────
@app.command("list-languages")
def list_languages() -> None:
    """List all supported language codes."""
    typer.echo("\nSupported languages:\n")
    for code, (name, native) in SUPPORTED_LANGUAGES.items():
        marker = " ← default" if code in DEFAULT_LANGUAGES else ""
        typer.echo(f"  {code:>4}  {name:<25} ({native}){marker}")
    typer.echo()


@app.command("translate")
def translate(
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
    # translator = HuggingFaceTranslator(source=None, target_langs=target_langs, dry_run=False)
    g_translator = GoogleTranslator(source=None, target_langs=target_langs, dry_run=False)
    db_url = "mysql+pymysql://root:fuelrod@localhost/translations"
    updater = TranslationDBUpdater(db_url=db_url, translator=g_translator)
    updater.update_missing()


@app.command("export")
def export(
        base_xml: str = typer.Option(
            getenv("BASE_XML", "strings.xml"),
            "--base",
            "-b",
            help="Path to the base English strings.xml file used to preserve key order."
        ),
        output_dir: str = typer.Option(
            getenv("OUTPUT_DIR", "res"),
            "--dir",
            "-d",
            help="Destination Android res directory where translations will be exported."
        ),
        db_url: str = typer.Option(
            getenv("DB_URL"),
            "--db-url",
            "-u",
            help="Database connection URL for the translations source."
        ),
        env_file: Optional[str] = typer.Option(
            None,
            "--env-file",
            "-e",
            help="Optional path to a .env file to load environment variables from."
        ),
) -> None:
    # Load .env automatically if present
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    exporter = AndroidStringsExporter(
        db_url=db_url,
        output_dir=output_dir,
        base_xml_path=base_xml
    )
    exporter.export()


if __name__ == "__main__":
    app()
