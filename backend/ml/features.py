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

# Phase 2 (XGBoost) adds: shots-on-target ratio, days-rest fatigue proxy, and a
# home/away venue-specific form split — on top of every Phase 1 feature.
FEATURE_ORDER_V2 = FEATURE_ORDER + [
    "home_sot_ratio",
    "away_sot_ratio",
    "home_days_rest",
    "away_days_rest",
    "home_venue_form_pts",
    "away_venue_form_pts",
]

# Phase 3 wires in the richer acquired data: each team's recent *market strength*
# (rolling average of bookmaker-implied win probability — available at inference
# from history even though the upcoming fixture has no odds) plus rolling
# possession / shots / corners.
FEATURE_ORDER_V3 = FEATURE_ORDER_V2 + [
    "home_market_strength",
    "away_market_strength",
    "home_shots_avg",
    "away_shots_avg",
    "home_possession_avg",
    "away_possession_avg",
    "home_corners_avg",
    "away_corners_avg",
]


# All recent-form helpers operate on a team's *canonical group* — the set of team
# ids that represent the same club across data sources (live + historical). This
# lets a live fixture's features draw on decades of football-data.co.uk history.


def _recent_finished(group_ids, before, limit=5):
    return list(
        Match.objects.filter(
            Q(home_team_id__in=group_ids) | Q(away_team_id__in=group_ids)
        )
        .filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .select_related("stats")
        .order_by("-kickoff")[:limit]
    )


def _points_for(group_ids, matches):
    pts = 0
    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue
        is_home = m.home_team_id in group_ids
        gf = m.home_score if is_home else m.away_score
        ga = m.away_score if is_home else m.home_score
        if gf > ga:
            pts += 3
        elif gf == ga:
            pts += 1
    return pts


def _goal_averages(group_ids, matches):
    scored, conceded, n = 0, 0, 0
    for m in matches:
        if m.home_score is None or m.away_score is None:
            continue
        is_home = m.home_team_id in group_ids
        scored += m.home_score if is_home else m.away_score
        conceded += m.away_score if is_home else m.home_score
        n += 1
    if n == 0:
        return 0.0, 0.0
    return round(scored / n, 3), round(conceded / n, 3)


def _xg_average(group_ids, matches):
    total, n = 0.0, 0
    for m in matches:
        stats = getattr(m, "stats", None)
        if stats is None:
            continue
        is_home = m.home_team_id in group_ids
        xg = stats.home_xg if is_home else stats.away_xg
        if xg is not None:
            total += xg
            n += 1
    return round(total / n, 3) if n else 0.0


def _h2h(home_ids, away_ids, before, limit=10):
    meetings = (
        Match.objects.filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .filter(
            Q(home_team_id__in=home_ids, away_team_id__in=away_ids)
            | Q(home_team_id__in=away_ids, away_team_id__in=home_ids)
        )
        .order_by("-kickoff")[:limit]
    )
    home_wins = draws = away_wins = 0
    for m in meetings:
        if m.home_score is None or m.away_score is None:
            continue
        home_is_home = m.home_team_id in home_ids
        home_goals = m.home_score if home_is_home else m.away_score
        away_goals = m.away_score if home_is_home else m.home_score
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
    home_ids = home.canonical_group_ids()
    away_ids = away.canonical_group_ids()

    home_recent = _recent_finished(home_ids, before)
    away_recent = _recent_finished(away_ids, before)
    home_gs, home_gc = _goal_averages(home_ids, home_recent)
    away_gs, away_gc = _goal_averages(away_ids, away_recent)
    h2h_h, h2h_d, h2h_a = _h2h(home_ids, away_ids, before)
    season = match.league.season
    home_pos = _position(home, match.league, season)
    away_pos = _position(away, match.league, season)

    return {
        "home_advantage": 1,
        "home_form_pts": _points_for(home_ids, home_recent),
        "away_form_pts": _points_for(away_ids, away_recent),
        "home_goals_scored_avg": home_gs,
        "away_goals_scored_avg": away_gs,
        "home_goals_conceded_avg": home_gc,
        "away_goals_conceded_avg": away_gc,
        "h2h_home_wins": h2h_h,
        "h2h_draws": h2h_d,
        "h2h_away_wins": h2h_a,
        "position_delta": (home_pos - away_pos) if home_pos and away_pos else 0,
        "home_xg_avg": _xg_average(home_ids, home_recent),
        "away_xg_avg": _xg_average(away_ids, away_recent),
    }


def _sot_ratio(group_ids, matches):
    """Shots-on-target / total-shots over recent matches (0..1)."""
    sot, shots = 0, 0
    for m in matches:
        stats = getattr(m, "stats", None)
        if stats is None:
            continue
        is_home = m.home_team_id in group_ids
        s = stats.home_shots if is_home else stats.away_shots
        t = stats.home_shots_on_target if is_home else stats.away_shots_on_target
        if s:
            shots += s
            sot += t or 0
    return round(sot / shots, 3) if shots else 0.0


def _days_rest(matches, before):
    """Days between this kickoff and the team's most recent finished match."""
    if not matches:
        return 0
    last = matches[0].kickoff  # most recent (queryset ordered -kickoff)
    delta = (before - last).days
    return max(delta, 0)


def _venue_form_pts(group_ids, before, is_home_fixture, limit=5):
    """Form points from the team's last N matches *at the same venue*."""
    if is_home_fixture:
        qs = Match.objects.filter(home_team_id__in=group_ids)
    else:
        qs = Match.objects.filter(away_team_id__in=group_ids)
    recent = list(
        qs.filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .order_by("-kickoff")[:limit]
    )
    return _points_for(group_ids, recent)


def get_features_v2(match_id: int) -> dict:
    """Phase 2 feature dict: all Phase 1 features plus venue/fatigue/SOT signals."""
    match = Match.objects.select_related(
        "home_team", "away_team", "league"
    ).get(pk=match_id)
    home, away, before = match.home_team, match.away_team, match.kickoff
    home_ids = home.canonical_group_ids()
    away_ids = away.canonical_group_ids()

    features = get_features(match_id)
    home_recent = _recent_finished(home_ids, before)
    away_recent = _recent_finished(away_ids, before)

    features.update(
        {
            "home_sot_ratio": _sot_ratio(home_ids, home_recent),
            "away_sot_ratio": _sot_ratio(away_ids, away_recent),
            "home_days_rest": _days_rest(home_recent, before),
            "away_days_rest": _days_rest(away_recent, before),
            "home_venue_form_pts": _venue_form_pts(home_ids, before, is_home_fixture=True),
            "away_venue_form_pts": _venue_form_pts(away_ids, before, is_home_fixture=False),
        }
    )
    return features


def _recent_with_data(group_ids, before, limit=10):
    """Recent finished matches with stats + odds prefetched (wider window for
    stable rolling averages)."""
    return list(
        Match.objects.filter(
            Q(home_team_id__in=group_ids) | Q(away_team_id__in=group_ids)
        )
        .filter(status=MatchStatus.FINISHED, kickoff__lt=before)
        .select_related("stats", "odds")
        .order_by("-kickoff")[:limit]
    )


def _team_stat_avg(group_ids, matches, home_attr, away_attr):
    """Average a per-team MatchStats attribute over matches where it's present."""
    vals = []
    for m in matches:
        stats = getattr(m, "stats", None)
        if stats is None:
            continue
        is_home = m.home_team_id in group_ids
        v = getattr(stats, home_attr if is_home else away_attr)
        if v is not None:
            vals.append(v)
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def _market_strength(group_ids, matches):
    """Mean bookmaker-implied win probability for the team over recent matches."""
    probs = []
    for m in matches:
        odds = getattr(m, "odds", None)
        if odds is None:
            continue
        implied = odds.implied_probabilities
        if not implied:
            continue
        is_home = m.home_team_id in group_ids
        probs.append(implied["home"] if is_home else implied["away"])
    return round(sum(probs) / len(probs), 4) if probs else 0.0


def get_features_v3(match_id: int) -> dict:
    """Phase 3 feature dict: v2 features plus market strength and rolling
    possession / shots / corners from the acquired stats + odds."""
    match = Match.objects.select_related(
        "home_team", "away_team", "league"
    ).get(pk=match_id)
    home, away, before = match.home_team, match.away_team, match.kickoff
    home_ids = home.canonical_group_ids()
    away_ids = away.canonical_group_ids()

    features = get_features_v2(match_id)
    hr = _recent_with_data(home_ids, before)
    ar = _recent_with_data(away_ids, before)

    features.update(
        {
            "home_market_strength": _market_strength(home_ids, hr),
            "away_market_strength": _market_strength(away_ids, ar),
            "home_shots_avg": _team_stat_avg(home_ids, hr, "home_shots", "away_shots"),
            "away_shots_avg": _team_stat_avg(away_ids, ar, "home_shots", "away_shots"),
            "home_possession_avg": _team_stat_avg(home_ids, hr, "home_possession", "away_possession"),
            "away_possession_avg": _team_stat_avg(away_ids, ar, "home_possession", "away_possession"),
            "home_corners_avg": _team_stat_avg(home_ids, hr, "home_corners", "away_corners"),
            "away_corners_avg": _team_stat_avg(away_ids, ar, "home_corners", "away_corners"),
        }
    )
    return features


def features_to_vector(features: dict, order=FEATURE_ORDER) -> list:
    """Flatten a feature dict into an ordered vector for the model."""
    return [features[name] for name in order]


# Registry mapping a model's feature-set name to its (builder, ordered keys).
FEATURE_SETS = {
    "v1": (get_features, FEATURE_ORDER),
    "v2": (get_features_v2, FEATURE_ORDER_V2),
    "v3": (get_features_v3, FEATURE_ORDER_V3),
}


def label_for(match: Match) -> str:
    """Training label: HOME / DRAW / AWAY from a finished match's score."""
    if match.home_score > match.away_score:
        return "HOME"
    if match.home_score == match.away_score:
        return "DRAW"
    return "AWAY"
