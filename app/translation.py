from abc import ABC, abstractmethod
from dataclasses import dataclass


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class TranslationRow:
    key: str
    source_text: str
    translations: dict[str, str | None]  # lang_code → existing value or None


# ── Source abstraction ────────────────────────────────────────────────────────
class TranslationSource(ABC):
    """Abstract base — implement to support any backend (xlsx, db, csv, …)."""

    @abstractmethod
    def load(self) -> list[TranslationRow]:
        """Read all rows from the source."""
        ...

    @abstractmethod
    def save(self, rows: list[TranslationRow]) -> None:
        """Persist translated rows back to the source."""
        ...

    @abstractmethod
    def describe(self) -> str:
        """Human-readable description of the source (for logging)."""
        ...
