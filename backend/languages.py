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

# Supported language codes by Sarvam STT & TTS APIs
VALID_SARVAM_CODES: set[str] = {
    "unknown", "hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN",
    "ta-IN", "te-IN", "en-IN", "gu-IN", "as-IN", "ur-IN", "ne-IN", "kok-IN",
    "ks-IN", "sd-IN", "sa-IN", "sat-IN", "mni-IN", "brx-IN", "mai-IN", "doi-IN",
}

# Mapping common 2-letter ISO-639-1 or shorthand codes to Sarvam BCP-47 tags
SARVAM_LANGUAGE_MAP: dict[str, str] = {
    "mr": "mr-IN",
    "hi": "hi-IN",
    "en": "en-IN",
    "gu": "gu-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "bn": "bn-IN",
    "od": "od-IN",
    "or": "od-IN",
    "as": "as-IN",
    "ur": "ur-IN",
    "ne": "ne-IN",
    "kok": "kok-IN",
    "ks": "ks-IN",
    "sd": "sd-IN",
    "sa": "sa-IN",
    "sat": "sat-IN",
    "mni": "mni-IN",
    "brx": "brx-IN",
    "mai": "mai-IN",
    "doi": "doi-IN",
}


def normalize_sarvam_language(code: str | None, default: str = "unknown") -> str:
    """Normalize language code to a valid Sarvam API format (e.g. 'mr' -> 'mr-IN')."""
    if not code:
        return default
    c = str(code).strip()
    if not c:
        return default
    if c in VALID_SARVAM_CODES:
        return c
    c_lower = c.lower()
    for valid in VALID_SARVAM_CODES:
        if c_lower == valid.lower():
            return valid
    prefix = c_lower.split("-")[0].split("_")[0]
    if prefix in SARVAM_LANGUAGE_MAP:
        return SARVAM_LANGUAGE_MAP[prefix]
    return default


def is_language_supported(lang: str | None, supported: list[str]) -> bool:
    """Check if requested language matches supported languages list,
    handling 2-letter vs BCP-47 representations ('mr' vs 'mr-IN')."""
    if not lang or not supported or "multilingual" in supported:
        return True
    lang_clean = lang.strip().lower()
    sup_clean = [s.strip().lower() for s in supported]
    if lang_clean in sup_clean:
        return True
    lang_base = lang_clean.split("-")[0].split("_")[0]
    for s in sup_clean:
        s_base = s.split("-")[0].split("_")[0]
        if lang_base == s_base:
            return True
    return False


def resolve(code: str | None) -> tuple[str, dict[str, str]]:
    """Return (canonical_code, info). Falls back to the default if unknown."""
    if not code:
        return DEFAULT_LANGUAGE, LANGUAGES[DEFAULT_LANGUAGE]
    clean = str(code).strip()
    if clean in LANGUAGES:
        return clean, LANGUAGES[clean]
    clean_lower = clean.lower()
    for k, v in LANGUAGES.items():
        if k.lower() == clean_lower:
            return k, v
    prefix = clean_lower.split("-")[0].split("_")[0]
    mapped = SARVAM_LANGUAGE_MAP.get(prefix) or SARVAM_LANGUAGE_MAP.get(clean_lower)
    if mapped and mapped in LANGUAGES:
        return mapped, LANGUAGES[mapped]
    return DEFAULT_LANGUAGE, LANGUAGES[DEFAULT_LANGUAGE]
