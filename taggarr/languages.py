"""Language code utilities using pycountry."""

import pycountry


def get_aliases(code_or_name):
    """Get all known aliases for a language (alpha_2, alpha_3, name, regional variants)."""
    if not code_or_name:
        return set()

    code_or_name = code_or_name.lower()
    aliases = set()

    try:
        lang = (
            pycountry.languages.get(alpha_2=code_or_name)
            or pycountry.languages.get(alpha_3=code_or_name)
            or pycountry.languages.lookup(code_or_name)
        )
    except Exception:
        return aliases

    if lang:
        if hasattr(lang, 'alpha_2'):
            aliases.add(lang.alpha_2.lower())
        if hasattr(lang, 'alpha_3'):
            aliases.add(lang.alpha_3.lower())
        aliases.add(lang.name.lower())

    # Add regional variants
    for suffix in ['-us', '-gb', '-ca', '-au', '-fr', '-de', '-jp', '-kr', '-cn', '-tw', '-ru']:
        aliases.update(a + suffix for a in list(aliases))

    return aliases


def get_primary_code(lang):
    """Get ISO 639-1 code (2-letter) for a language."""
    try:
        result = pycountry.languages.get(name=lang) or pycountry.languages.lookup(lang)
        return result.alpha_2.lower()
    except Exception:
        return lang.lower()[:2]


def build_language_codes(target_languages):
    """Build set of all acceptable language codes from target languages."""
    codes = set()
    for lang in target_languages:
        codes.update(get_aliases(lang))
    return codes
