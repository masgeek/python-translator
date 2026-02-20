# ── Language definitions ──────────────────────────────────────────────────────
from pathlib import Path
from dotenv import load_dotenv

import os

# Determine project root
BASE_DIR = Path(__file__).resolve().parent.parent  # adjust if needed

# Load .env file
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path)

SUPPORTED_LANGUAGES: dict[str, tuple[str, str]] = {
    "rw": ("Kinyarwanda", "Ikinyarwanda"),
    "sw": ("Tanzanian Swahili", "Kiswahili cha Tanzania"),
}

DEFAULT_LANGUAGES = ["sw"]
SOURCE_LANG = "English"
SOURCE_CODE = "en"
MODEL = "translategemma"

# DEFAULT_PROMPT = (
#     "You are a professional {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) translator. "
#     "Your goal is to accurately convey the meaning and nuances of the original {SOURCE_LANG} text "
#     "while adhering to {TARGET_LANG} grammar, vocabulary, and cultural sensitivities.\n"
#     "Produce only the {TARGET_LANG} translation, without any additional explanations or commentary. "
#     "Please translate the following {SOURCE_LANG} text into {TARGET_LANG}:\n\n"
#     "{TEXT}"
# )

DEFAULT_PROMPT = (
    "Translate from {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) for android mobile application localization"
)
# override dictionary for problematic terms
# Swahili/Kinyarwanda overrides
TRANSLATION_OVERRIDES = {
    "sw": {
        "feedback": "maoni",
        "username": "jina la mtumiaji",
        "password": "nenosiri",
    },
    "rw": {
        "feedback": "ibitekerezo",
    },
}

# os.environ['HF_TOKEN'] = os.getenv("HF_TOKEN")

HF_TOKEN = os.getenv("HF_TOKEN")
GOOGLE_TRANSLATOR_KEY = os.getenv("GOOGLE_TRANSLATOR_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", 'akilimo')
