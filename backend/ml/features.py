"""Feature engineering for match outcome prediction (Phase 1 — logistic regression).

The public entry point is ``get_features(match_id)`` which returns the flat dict
described in CLAUDE.md. All helpers only look at data available *before* kickoff
so the same code can build training features and live inference features.
"""
from django.db.models import Q

from apps.leagues.models import Standing
from apps.matches.models import Match, MatchStatus

FEATURE_ORDER = [
    "home_advantage",
    "home_form_pts",
    "away_form_pts",
    "home_goals_scored_avg",
    "away_goals_scored_avg",
    "home_goals_conceded_avg",
    "away_goals_conceded_avg",
    "h2h_home_wins",
    "h2h_draws",
    "h2h_away_wins",
    "position_delta",
    "home_xg_avg",
    "away_xg_avg",
]


def _recent_finished(team, before, limit=5):
    return list(
        Match.objects.filter(Q(home_team=team) | Q(away_team=team))
        .filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .select_related("stats")
        .order_by("-kickoff")[:limit]
    )


def _points_for(team, matches):
    pts = 0
    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue
        is_home = m.home_team_id == team.id
        gf = m.home_score if is_home else m.away_score
        ga = m.away_score if is_home else m.home_score
        if gf > ga:
            pts += 3
        elif gf == ga:
            pts += 1
    return pts


def _goal_averages(team, matches):
    scored, conceded, n = 0, 0, 0
    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue
        is_home = m.home_team_id == team.id
        scored += m.home_score if is_home else m.away_score
        conceded += m.away_score if is_home else m.home_score
        n += 1
    if n == 0:
        return 0.0, 0.0
    return round(scored / n, 3), round(conceded / n, 3)


def _xg_average(team, matches):
    total, n = 0.0, 0
    for m in matches:
        stats = getattr(m, "stats", None)
        if stats is None:
            continue
        is_home = m.home_team_id == team.id
        xg = stats.home_xg if is_home else stats.away_xg
        if xg is not None:
            total += xg
            n += 1
    return round(total / n, 3) if n else 0.0


def _h2h(home, away, before, limit=10):
    meetings = (
        Match.objects.filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .filter(
            Q(home_team=home, away_team=away) | Q(home_team=away, away_team=home)
        )
        .order_by("-kickoff")[:limit]
    )
    home_wins = draws = away_wins = 0
    for m in meetings:
        if m.home_score is None or m.away_score is None:
            continue
        home_goals = m.home_score if m.home_team_id == home.id else m.away_score
        away_goals = m.away_score if m.home_team_id == home.id else m.home_score
        if home_goals > away_goals:
            home_wins += 1
        elif home_goals == away_goals:
            draws += 1
        else:
            away_wins += 1
    return home_wins, draws, away_wins


def _position(team, league, season):
    standing = Standing.objects.filter(
        league=league, team=team, season=season
    ).first()
    return standing.position if standing else 0


def get_features(match_id: int) -> dict:
    """Return the flat feature dict for a match (see CLAUDE.md schema)."""
    match = Match.objects.select_related(
        "home_team", "away_team", "league"
    ).get(pk=match_id)
    home, away, before = match.home_team, match.away_team, match.kickoff

    home_recent = _recent_finished(home, before)
    away_recent = _recent_finished(away, before)
    home_gs, home_gc = _goal_averages(home, home_recent)
    away_gs, away_gc = _goal_averages(away, away_recent)
    h2h_h, h2h_d, h2h_a = _h2h(home, away, before)
    season = match.league.season
    home_pos = _position(home, match.league, season)
    away_pos = _position(away, match.league, season)

    return {
        "home_advantage": 1,
        "home_form_pts": _points_for(home, home_recent),
        "away_form_pts": _points_for(away, away_recent),
        "home_goals_scored_avg": home_gs,
        "away_goals_scored_avg": away_gs,
        "home_goals_conceded_avg": home_gc,
        "away_goals_conceded_avg": away_gc,
        "h2h_home_wins": h2h_h,
        "h2h_draws": h2h_d,
        "h2h_away_wins": h2h_a,
        "position_delta": (home_pos - away_pos) if home_pos and away_pos else 0,
        "home_xg_avg": _xg_average(home, home_recent),
        "away_xg_avg": _xg_average(away, away_recent),
    }


def features_to_vector(features: dict) -> list:
    """Flatten a feature dict into an ordered vector for the model."""
    return [features[name] for name in FEATURE_ORDER]


def label_for(match: Match) -> str:
    """Training label: HOME / DRAW / AWAY from a finished match's score."""
    if match.home_score > match.away_score:
        return "HOME"
    if match.home_score == match.away_score:
        return "DRAW"
    return "AWAY"
