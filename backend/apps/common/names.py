"""Name sanitising shared by the ingest commands.

Each upstream feed mangles apostrophes in its own way — Understat HTML-escapes
them ("Matt O&#039;Riley"), StatsBomb SQL-escapes them ("Gary O''Neil") — and
the damage reaches player, coach, referee and stadium names alike. Normalising
in one place keeps the next ingest from reinventing it.
"""
import html
import re

_DOUBLED_APOSTROPHE = re.compile(r"'{2,}")


def clean_name(value):
    """Undo feed-specific escaping. Non-strings pass through untouched."""
    if not isinstance(value, str):
        return value
    return _DOUBLED_APOSTROPHE.sub("'", html.unescape(value)).strip()
