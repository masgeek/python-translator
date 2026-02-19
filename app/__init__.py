# ── Language definitions ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES: dict[str, tuple[str, str]] = {
    "rw": ("Kinyarwanda", "Ikinyarwanda"),
    "sw": ("Tanzanian Swahili", "Kiswahili cha Tanzania"),
    "fr": ("French", "Français"),
}

DEFAULT_LANGUAGES = ["rw", "sw"]
SOURCE_LANG = "English"
SOURCE_CODE = "en"
MODEL = "translategemma"

DEFAULT_PROMPT = (
    "You are a professional {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) translator. "
    "Your goal is to accurately convey the meaning and nuances of the original {SOURCE_LANG} text "
    "while adhering to {TARGET_LANG} grammar, vocabulary, and cultural sensitivities.\n"
    "Produce only the {TARGET_LANG} translation, without any additional explanations or commentary. "
    "Please translate the following {SOURCE_LANG} text into {TARGET_LANG}:\n\n"
    "{TEXT}"
)
