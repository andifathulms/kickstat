"""Phase 3 — Poisson scoreline model.

Models each team's goals as an independent Poisson process. Team attack/defence
strengths are estimated from recent goal rates (over the canonical match history),
scaled by league baselines, to get expected goals (lambda) per side. The product
of the two Poisson distributions gives the full scoreline probability grid, from
which we read the most-likely score and 1X2 / over-2.5 / BTTS probabilities.

Parametric — no trained model file; computed from form at prediction time.
"""
import math

from django.db.models import Avg, Q

from apps.matches.models import Match, MatchStatus

MODEL_VERSION = "poisson_v1"
MAX_GOALS = 8  # scoreline grid 0..8 captures ~all probability mass

_baseline_cache = {}


def _poisson_pmf(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)


def league_baseline(refresh=False):
    """Global mean home/away goals across finished matches (cached per process)."""
    if refresh or "b" not in _baseline_cache:
        agg = (
            Match.objects.filter(status=MatchStatus.FINISHED)
            .exclude(home_score=None)
            .exclude(away_score=None)
            .aggregate(h=Avg("home_score"), a=Avg("away_score"))
        )
        _baseline_cache["b"] = (agg["h"] or 1.45, agg["a"] or 1.15)
    return _baseline_cache["b"]


def _team_goal_rates(group_ids, before, limit=10):
    """Average goals scored/conceded over a team's recent finished matches.

    Returns (avg_scored, avg_conceded) or (None, None) if no history.
    """
    matches = (
        Match.objects.filter(
            Q(home_team_id__in=group_ids) | Q(away_team_id__in=group_ids)
        )
        .filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .exclude(home_score=None)
        .exclude(away_score=None)
        .order_by("-kickoff")[:limit]
    )
    scored = conceded = n = 0
    for m in matches:
        is_home = m.home_team_id in group_ids
        scored += m.home_score if is_home else m.away_score
        conceded += m.away_score if is_home else m.home_score
        n += 1
    if n == 0:
        return None, None
    return scored / n, conceded / n


def predict_scoreline(match_id, baseline=None):
    """Return the Poisson scoreline prediction for a match as a flat dict."""
    match = Match.objects.select_related("home_team", "away_team").get(pk=match_id)
    home_ids = match.home_team.canonical_group_ids()
    away_ids = match.away_team.canonical_group_ids()
    before = match.kickoff

    home_avg, away_avg = baseline or league_baseline()
    overall = (home_avg + away_avg) / 2  # mean goals per team per match

    h_scored, h_conceded = _team_goal_rates(home_ids, before)
    a_scored, a_conceded = _team_goal_rates(away_ids, before)

    home_attack = (h_scored / overall) if h_scored is not None else 1.0
    home_defence = (h_conceded / overall) if h_conceded is not None else 1.0
    away_attack = (a_scored / overall) if a_scored is not None else 1.0
    away_defence = (a_conceded / overall) if a_conceded is not None else 1.0

    lam_home = _clamp(home_avg * home_attack * away_defence)
    lam_away = _clamp(away_avg * away_attack * home_defence)

    grid = [
        [_poisson_pmf(i, lam_home) * _poisson_pmf(j, lam_away) for j in range(MAX_GOALS + 1)]
        for i in range(MAX_GOALS + 1)
    ]
    total = sum(sum(row) for row in grid)  # ~1.0; normalise for safety

    home_win = draw = away_win = over25 = btts = 0.0
    flat = []
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = grid[i][j] / total
            flat.append((i, j, p))
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if i + j >= 3:
                over25 += p
            if i >= 1 and j >= 1:
                btts += p

    flat.sort(key=lambda t: -t[2])
    top = [{"home": i, "away": j, "prob": round(p, 4)} for i, j, p in flat[:5]]
    mlh, mla, mlp = flat[0]

    return {
        "lambda_home": round(lam_home, 3),
        "lambda_away": round(lam_away, 3),
        "most_likely_home": mlh,
        "most_likely_away": mla,
        "most_likely_prob": round(mlp, 4),
        "home_win_prob": round(home_win, 4),
        "draw_prob": round(draw, 4),
        "away_win_prob": round(away_win, 4),
        "over25_prob": round(over25, 4),
        "btts_prob": round(btts, 4),
        "top_scores": top,
        "model_version": MODEL_VERSION,
    }


def _clamp(lam, lo=0.15, hi=6.0):
    return min(max(lam, lo), hi)
