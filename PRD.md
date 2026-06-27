# PRD — Kickstat

## Overview

Kickstat is a public-facing football analytics platform covering major European leagues (Premier League, La Liga, Serie A, Bundesliga, Champions League) and Indonesian Liga 1. It combines live scores, match statistics, league standings, and AI-powered match predictions in a single clean interface. The primary audience is football fans who want more than just scores — they want context, data, and insight.

Primary language: English. Indonesian (ID) i18n to be added in a later phase via next-intl.

---

## Goals

- Deliver live scores and match center for all covered leagues
- Surface match predictions with probability breakdowns before kickoff
- Provide league standings, team stats, and historical form analysis
- Store all ingested data in PostgreSQL for trend analysis over time
- Keep infrastructure cost at zero (free API tiers only)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Frontend | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Charts | Recharts + D3.js |
| Container | Docker + Docker Compose |
| Deployment | GCP VM (Nginx reverse proxy) |

---

## Data Sources

### Primary — football-data.org
- Free, no daily cap, 10 req/min
- Covers: Premier League, La Liga, Serie A, Bundesliga, Champions League
- Provides: fixtures, results, standings, scorers, lineups

### Secondary — API-Football (api-sports.io)
- Free tier: 100 req/day
- Use ONLY for: Indonesian Liga 1 (not available on football-data.org)
- Conserve quota by syncing Liga 1 once daily, not live

### ML Training Data — StatsBomb Open Data (GitHub)
- Free historical match event data: xG, passes, shots, pressure events
- Pull once → store in DB → train prediction model offline
- Not used for live data

---

## Database Models

### League
```
id, name, country, source (football-data | api-football), external_id, season, is_active
```

### Team
```
id, name, short_name, league FK, external_id, logo_url, source
```

### Player
```
id, name, position, nationality, date_of_birth, team FK, external_id
```

### Match
```
id, league FK, home_team FK, away_team FK, matchday, kickoff (datetime), status
(SCHEDULED | LIVE | FINISHED | POSTPONED | CANCELLED),
home_score, away_score, external_id (unique), raw_data (JSONField)
```

### MatchStats
```
id, match OneToOne, home_possession, away_possession,
home_shots, away_shots, home_shots_on_target, away_shots_on_target,
home_corners, away_corners, home_fouls, away_fouls,
home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards,
home_xg, away_xg
```

### MatchEvent
```
id, match FK, minute, type (GOAL | YELLOW | RED | SUBSTITUTION | VAR),
team FK, player FK, detail (JSONField)
```

### Standing
```
id, league FK, team FK, season, position, played, won, drawn, lost,
goals_for, goals_against, goal_difference, points
```

### MatchPrediction
```
id, match OneToOne, home_win_prob, draw_prob, away_win_prob,
predicted_outcome (HOME | DRAW | AWAY), model_version,
confidence_score, created_at, was_correct (nullable, filled post-match)
```

---

## API Sync Architecture (Celery Beat)

```
CELERYBEAT_SCHEDULE = {
    # football-data.org tasks (safe — no daily cap)
    'sync-standings':        daily at 06:00 WIB
    'sync-fixtures-7days':   daily at 06:30 WIB
    'sync-live-scores':      every 5 minutes (only active on matchdays)
    'sync-finished-matches': daily at 23:30 WIB (fill stats after games end)

    # api-football tasks (Liga 1 only — conserve 100 req/day quota)
    'sync-liga1-fixtures':   weekly on Monday 05:00 WIB
    'sync-liga1-results':    daily at 23:00 WIB (only on Liga 1 matchdays)

    # Prediction tasks
    'run-predictions':       daily at 08:00 WIB (for today's fixtures)
    'evaluate-predictions':  daily at 00:00 WIB (score yesterday's predictions)
}
```

**Rate limit safety**: Wrap all football-data.org tasks with a `time.sleep(6)` between requests to stay under 10 req/min.

---

## Prediction Model

### Phase 1 — Logistic Regression (MVP)
Features:
- Home advantage (binary)
- Last 5 match points for home team
- Last 5 match points for away team
- Average goals scored/conceded (last 5)
- Head-to-head record (last 10 meetings)
- Current league position delta

Output: `[home_win_prob, draw_prob, away_win_prob]`

### Phase 2 — XGBoost
Additional features:
- xG rolling average (from StatsBomb historical + accumulated live data)
- Shots on target ratio
- Days since last match (fatigue proxy)
- Home/away form split (separate from overall form)

### Phase 3 — Poisson Score Predictor
- Model goal rates independently per team
- Predict full scoreline probability distribution
- Surface "most likely score" on match card

### Model Versioning
- Store `model_version` string on each `MatchPrediction`
- Evaluate accuracy per version via `was_correct` field
- Retrain monthly as data accumulates

---

## DRF API Endpoints

```
GET /api/leagues/                          → list all leagues
GET /api/leagues/{id}/standings/           → current standings
GET /api/leagues/{id}/fixtures/            → upcoming fixtures
GET /api/leagues/{id}/results/             → recent results

GET /api/matches/live/                     → currently live matches
GET /api/matches/{id}/                     → match detail
GET /api/matches/{id}/stats/               → match statistics
GET /api/matches/{id}/events/              → timeline of events
GET /api/matches/{id}/prediction/          → AI prediction

GET /api/teams/{id}/                       → team detail
GET /api/teams/{id}/form/                  → last 5 match form
GET /api/teams/{id}/fixtures/              → upcoming fixtures
GET /api/teams/{id}/stats/                 → season statistics
```

---

## Frontend Pages (Next.js App Router)

```
/                          → Home: live now, today's fixtures, top predictions
/league/[slug]             → League hub: standings, fixtures, top scorers
/match/[id]                → Match center: live score, stats, events, prediction
/team/[id]                 → Team page: form, squad, fixtures, stats
/predictions               → Prediction hub: today's AI picks with confidence bars
/standings                 → All leagues standings at a glance
```

### Home Page Layout
- Hero: Live matches ticker (auto-refresh every 60s)
- Section 1: Today's fixtures grouped by league
- Section 2: Top AI predictions for today (3 cards, confidence %)
- Section 3: Recent results
- Section 4: League standings snapshot (tabs per league)

### Match Center Layout
- Header: Teams, score, live minute
- Tab 1: Overview (key events timeline, H2H record)
- Tab 2: Stats (possession bar, shot maps, stat bars)
- Tab 3: Prediction (probability donut chart, model explanation)
- Tab 4: Lineups

---

## Design System — "Pitch Dark"

**Philosophy**: Data-dense, dark-first, feels like a premium sports app. Stats should breathe. Scores should pop.

**Color Palette**
```
--pitch-black:    #0D0F12   (background)
--surface:        #161A1F   (cards, panels)
--surface-raised: #1E232A   (elevated elements)
--border:         #2A3038   (dividers)
--grass-green:    #00D46A   (primary accent — live indicators, wins, CTA)
--amber-goal:     #FFB800   (goals, highlights, draws)
--red-card:       #FF3B3B   (losses, red cards, danger)
--text-primary:   #F0F2F5   (headings, scores)
--text-secondary: #8A96A3   (labels, metadata)
```

**Typography**
- Display/Scores: `DM Mono` — numbers feel athletic and precise
- UI/Body: `Inter` — clean, neutral, excellent at small sizes
- Stat labels: `Inter` 11px uppercase tracking-widest

**Signature element**: Live match cards pulse with a subtle green glow animation on the border. The live minute counter increments in real-time client-side.

---

## Phase Plan

### Phase 1 — Core Infrastructure (Week 1–2)
- [ ] Django project setup with all models
- [ ] Celery + Redis sync tasks for football-data.org
- [ ] Admin panel to monitor sync health
- [ ] DRF endpoints for leagues, matches, standings
- [ ] Basic Next.js scaffold with design system tokens

### Phase 2 — Live Match Center (Week 3–4)
- [ ] Live scores page with auto-refresh
- [ ] Match detail page: events, stats, lineups
- [ ] Today's fixtures grouped by league
- [ ] League standings pages

### Phase 3 — Predictions (Week 5–6)
- [ ] StatsBomb data ingestion script
- [ ] Feature engineering pipeline
- [ ] Logistic regression model training
- [ ] Prediction API endpoint + match prediction UI

### Phase 4 — Liga 1 + Polish (Week 7–8)
- [ ] API-Football integration for Liga 1
- [ ] Team pages with form + stats
- [ ] Prediction accuracy dashboard (admin)
- [ ] SEO: sitemap, metadata per match/league
- [ ] Mobile responsive polish

### Phase 5 — i18n (Future)
- [ ] next-intl setup
- [ ] Indonesian translation strings
- [ ] ID locale number/date formatting

---

## Out of Scope (v1)
- User accounts / favourites
- Push notifications
- Fantasy football
- Betting odds integration
- Video highlights
