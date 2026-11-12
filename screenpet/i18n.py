"""Dil desteği. Metinler languages.json dosyasından okunur."""

import json

from . import paths

DEFAULT_LANGUAGE = "tr"
FALLBACK_LANGUAGE = "en"

_languages = {}
_current = DEFAULT_LANGUAGE


def load(path=None):
    global _languages
    path = path or paths.resource_path(paths.LANGUAGE_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            _languages = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Dil dosyası okunamadı ({path}): {e}")
        _languages = {}
    return _languages


def available():
    return list(_languages.keys())


def set_language(code):
    global _current
    _current = code if code in _languages else DEFAULT_LANGUAGE


def get_language():
    return _current


def _lookup(key):
    for code in (_current, DEFAULT_LANGUAGE, FALLBACK_LANGUAGE):
        text = _languages.get(code, {}).get(key)
        if text is not None:
            return text
    return key


def t(key, **kwargs):
    """Anahtarın geçerli dildeki metni. Yoksa diğer dile, o da yoksa anahtara düşer."""
    text = _lookup(key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def tn(key, n, **kwargs):
    """Sayıya göre tekil/çoğul metin. `key_one` varsa n == 1 için onu kullanır."""
    one_key = f"{key}_one"
    if n == 1 and _languages.get(_current, {}).get(one_key) is not None:
        key = one_key
    return t(key, n=n, **kwargs)
