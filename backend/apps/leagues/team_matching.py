"""Match team names across data sources (football-data.org vs football-data.co.uk).

The two sources name the same club differently — "Manchester City FC" vs
"Man City", "Wolverhampton Wanderers FC" vs "Wolves". ``match_name`` resolves a
source name to a canonical name within a constrained candidate pool (same league)
using, in order: exact normalized match, token-subset, a curated alias map, then
fuzzy ratio. Kept pure (no DB) so it is easily unit-tested.
"""
import difflib
import re
import unicodedata

# Common club-name tokens that carry no distinguishing information once both
# sides are normalized. Stripping them helps "AC Milan" == "Milan", etc.
_NOISE_TOKENS = {
    "fc", "cf", "afc", "sc", "ac", "as", "us", "ss", "ssc", "cd", "ud", "rc",
    "fk", "bk", "if", "sv", "vfl", "vfb", "tsg", "rcd", "sd", "club", "calcio",
}

# Curated aliases for abbreviations that fuzzy/subset matching misses.
# Keyed by normalized short form -> normalized canonical form.
_ALIASES = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "man united": "manchester united",
    "nottm forest": "nottingham forest",
    "wolves": "wolverhampton wanderers",
    "sheffield weds": "sheffield wednesday",
    "qpr": "queens park rangers",
    "west brom": "west bromwich albion",
    "spurs": "tottenham hotspur",
    "ath bilbao": "athletic club",
    "ath madrid": "atletico madrid",
    "atletico": "atletico madrid",
    "sociedad": "real sociedad",
    "betis": "real betis",
    "espanol": "espanyol",
    "alaves": "deportivo alaves",
    "inter": "internazionale",
    "milan": "ac milan",
    "verona": "hellas verona",
    "dortmund": "borussia dortmund",
    "leverkusen": "bayer leverkusen",
    "bayern munich": "bayern munchen",
    "ein frankfurt": "eintracht frankfurt",
    "fc koln": "koln",
    "mgladbach": "borussia monchengladbach",
    "paris sg": "paris saint germain",
    "psg": "paris saint germain",
    "st etienne": "saint etienne",
    "olympique lyonnais": "lyon",
    "stade brestois 29": "brest",
    "stade rennais 1901": "rennes",
    "ajax": "ajax",
    "psv eindhoven": "psv",
    "sporting": "sporting cp",
    "porto": "fc porto",
    "sporting clube de braga": "sp braga",
    "vitoria": "guimaraes",
}


def normalize(name: str) -> str:
    """Lowercase, strip accents, drop noise tokens and punctuation."""
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = n.lower()
    n = n.replace("&", " and ").replace("'", "")
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    tokens = [t for t in n.split() if t and t not in _NOISE_TOKENS]
    return " ".join(tokens)


def _tokens(norm: str) -> set:
    return set(norm.split())


def match_name(name: str, candidates: list[str], cutoff: float = 0.82):
    """Return the best-matching candidate for ``name``, or None.

    ``candidates`` are raw candidate names; the returned value is the raw
    candidate that matched (not its normalized form).
    """
    target = normalize(name)
    if not target:
        return None
    norm_map = {}  # normalized -> raw (first wins)
    for c in candidates:
        norm_map.setdefault(normalize(c), c)

    # 1. exact normalized
    if target in norm_map:
        return norm_map[target]

    # 2. alias map (apply to both the target and to candidates)
    aliased = _ALIASES.get(target)
    if aliased and aliased in norm_map:
        return norm_map[aliased]
    for cnorm, raw in norm_map.items():
        if _ALIASES.get(cnorm) == target:
            return raw

    # 3. token-subset (one name's tokens fully contained in the other's)
    t_tokens = _tokens(target)
    best_subset = None
    for cnorm, raw in norm_map.items():
        c_tokens = _tokens(cnorm)
        if t_tokens and (t_tokens <= c_tokens or c_tokens <= t_tokens):
            # prefer the closest-length candidate
            if best_subset is None or abs(len(cnorm) - len(target)) < best_subset[0]:
                best_subset = (abs(len(cnorm) - len(target)), raw)
    if best_subset:
        return best_subset[1]

    # 4. fuzzy ratio fallback
    close = difflib.get_close_matches(target, list(norm_map), n=1, cutoff=cutoff)
    if close:
        return norm_map[close[0]]
    return None
