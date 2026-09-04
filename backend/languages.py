"""Supported call languages (Indian-focused, backed by Sarvam Bulbul).

Each entry maps a Sarvam BCP-47 code to the Whisper STT code and display names.
The admin picks one of these per call; it drives STT, the LLM reply language,
and the TTS voice together.
"""

# key = Sarvam target_language_code
LANGUAGES: dict[str, dict[str, str]] = {
    "en-IN": {"name": "English", "native": "English", "whisper": "en"},
    "hi-IN": {"name": "Hindi", "native": "हिन्दी", "whisper": "hi"},
    "bn-IN": {"name": "Bengali", "native": "বাংলা", "whisper": "bn"},
    "gu-IN": {"name": "Gujarati", "native": "ગુજરાતી", "whisper": "gu"},
    "kn-IN": {"name": "Kannada", "native": "ಕನ್ನಡ", "whisper": "kn"},
    "ml-IN": {"name": "Malayalam", "native": "മലയാളം", "whisper": "ml"},
    "mr-IN": {"name": "Marathi", "native": "मराठी", "whisper": "mr"},
    "od-IN": {"name": "Odia", "native": "ଓଡ଼ିଆ", "whisper": "or"},
    "pa-IN": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "whisper": "pa"},
    "ta-IN": {"name": "Tamil", "native": "தமிழ்", "whisper": "ta"},
    "te-IN": {"name": "Telugu", "native": "తెలుగు", "whisper": "te"},
}

DEFAULT_LANGUAGE = "en-IN"


def resolve(code: str | None) -> tuple[str, dict[str, str]]:
    """Return (canonical_code, info). Falls back to the default if unknown."""
    if code and code in LANGUAGES:
        return code, LANGUAGES[code]
    return DEFAULT_LANGUAGE, LANGUAGES[DEFAULT_LANGUAGE]
