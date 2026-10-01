"""Latin Mongolian (galig), as people type it, into Cyrillic for place search.

Cyrillic and digits stay as they are. English catalog names are not rewritten here; the resolver tries the
original spelling first and this form only when that finds nothing.
"""

import re

# Longer tokens first. "ayl" covers the common shortening aylal → аялал.
_TOKENS = (
    ("sh", "ш"),
    ("ch", "ч"),
    ("ts", "ц"),
    ("kh", "х"),
    ("zh", "ж"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ye", "е"),
    ("ayl", "аял"),
    ("ruu", "рүү"),
    ("ii", "ий"),
    ("ai", "ай"),
    ("ei", "эй"),
    ("oi", "ой"),
    ("ui", "уй"),
    ("uu", "уу"),
    ("aa", "аа"),
    ("oo", "оо"),
    ("ee", "ээ"),
)

_LETTER = {
    "a": "а",
    "b": "б",
    "c": "ц",
    "d": "д",
    "e": "э",
    "f": "ф",
    "g": "г",
    "h": "х",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "к",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "w": "в",
    "x": "х",
    "y": "й",
    "z": "з",
    "ö": "ө",
    "ü": "ү",
}


def _word(token: str) -> str:
    i = 0
    out: list[str] = []
    while i < len(token):
        for src, dst in _TOKENS:
            if token.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(_LETTER.get(token[i], token[i]))
            i += 1
    return "".join(out)


def latin_to_cyrillic(text: str) -> str:
    """Turn galig letters into Cyrillic. A word that is already Cyrillic is unchanged."""
    return re.sub(r"[A-Za-zöüÖÜ]+", lambda match: _word(match.group(0).lower()), text)
