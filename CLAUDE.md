# CLAUDE.md — Kickstat

## What You Are Building

Kickstat is a public-facing football analytics platform. It ingests data from football-data.org (European leagues) and API-Football (Liga 1), stores everything in PostgreSQL, and surfaces live scores, match stats, league standings, and AI match predictions to users via a Next.js frontend.

Read PRD.md first. This file contains build instructions, conventions, and decisions already made. Do not deviate from them unless explicitly instructed.

---

## Repository Structure

```
kickstat/
├── backend/
│   ├── config/                  # Django settings, urls, celery
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   ├── celery.py
│   │   └── urls.py
│   ├── apps/
│   │   ├── leagues/             # League, Team, Standing models + endpoints
│   │   ├── matches/             # Match, MatchStats, MatchEvent models + endpoints
│   │   ├── predictions/         # MatchPrediction model, ML pipeline
│   │   └── sync/                # All Celery tasks for API ingestion
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # Reusable UI components
│   │   ├── lib/                 # API client, utils, hooks
│   │   └── styles/              # Global CSS, design tokens
│   ├── package.json
│   └── next.config.js
├── docker-compose.yml
├── docker-compose.prod.yml
└── nginx/
    └── kickstat.conf
```

---

## Environment Variables

```env
# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=

# Database
DATABASE_URL=postgresql://kickstat:password@db:5432/kickstat

# Redis
REDIS_URL=redis://redis:6379/0

# Football APIs
FOOTBALL_DATA_API_KEY=          # football-data.org key
API_FOOTBALL_KEY=               # api-sports.io key

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Django Conventions

- Django 5 + DRF 3.15+
- Use `split settings`: `base.py`, `local.py`, `production.py`
- All apps live under `backend/apps/`
- Use `external_id` CharField on all models that map to an API resource
- Store full API response in `raw_data = models.JSONField()` for reprocessing without re-fetching
- All DateTimeFields store UTC; display conversion happens on the frontend
- Use `select_related` and `prefetch_related` on all list endpoints — never N+1

### Model conventions
```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```
All models inherit from `BaseModel`.

---

## Celery Task Conventions

- All sync tasks live in `apps/sync/tasks/`
- One file per data source: `football_data.py`, `api_football.py`
- Every task must be idempotent: use `update_or_create` with `external_id` as lookup
- Add `time.sleep(6)` between requests to football-data.org to respect 10 req/min limit
- API-Football tasks: track daily request count in Redis; abort if approaching 90/day
- Log every sync with: records_created, records_updated, errors, duration_ms

```python
# Task signature pattern
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_fixtures(self, league_id: int):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

## DRF Conventions

- Use `ModelViewSet` for standard CRUD, `APIView` for custom endpoints
- All list endpoints paginated: `PageNumberPagination`, page_size=20
- All responses include `count`, `next`, `previous`, `results`
- Serializers: use `depth=1` sparingly; prefer explicit nested serializers
- No authentication required for read endpoints (public API)
- Use `django-filter` for filtering by league, status, date

### URL pattern
```python
# config/urls.py
urlpatterns = [
    path('api/', include('apps.leagues.urls')),
    path('api/', include('apps.matches.urls')),
    path('api/', include('apps.predictions.urls')),
    path('admin/', admin.site.urls),
]
```

---

## Prediction Pipeline

### Data flow
```
StatsBomb GitHub → management command → MatchStats rows
Accumulated match data → feature_engineering.py → features DataFrame
features DataFrame → train.py → model.pkl (stored in /backend/ml/models/)
Celery task → load model.pkl → predict today's fixtures → MatchPrediction rows
DRF endpoint → serve predictions to frontend
```

### Files
```
backend/
└── ml/
    ├── features.py          # Feature engineering functions
    ├── train.py             # Model training script (run manually or monthly)
    ├── predict.py           # Inference for a given match
    ├── evaluate.py          # Accuracy scoring against was_correct field
    └── models/              # Serialized model files (.pkl)
        └── v1_logistic.pkl
```

### Feature engineering — `get_features(match_id)`
Must return a flat dict:
```python
{
    'home_advantage': 1,
    'home_form_pts': 7,          # last 5 matches
    'away_form_pts': 10,
    'home_goals_scored_avg': 1.8,
    'away_goals_scored_avg': 2.1,
    'home_goals_conceded_avg': 1.2,
    'away_goals_conceded_avg': 0.9,
    'h2h_home_wins': 3,
    'h2h_draws': 1,
    'h2h_away_wins': 1,
    'position_delta': 4,          # home_position - away_position
    'home_xg_avg': 1.6,
    'away_xg_avg': 1.9,
}
```

---

## Frontend Conventions

- Next.js 14 App Router (no Pages router)
- All data fetching via server components where possible; use `use client` only for interactive elements
- API calls centralized in `src/lib/api.ts`
- Design tokens in `src/styles/tokens.css` as CSS custom properties (see Design System in PRD)
- Tailwind config extended with Kickstat palette — do not hardcode hex values in components
- Auto-refresh for live scores: use `setInterval` in a client component, 60s interval, only when `match.status === 'LIVE'`

### Component naming
```
/components/
├── match/
│   ├── MatchCard.tsx          # compact card for fixture lists
│   ├── MatchCenter.tsx        # full match detail layout
│   ├── LiveTicker.tsx         # scrolling live scores bar
│   ├── StatBar.tsx            # horizontal possession/shots bar
│   └── PredictionDonut.tsx    # recharts donut for probabilities
├── league/
│   ├── StandingsTable.tsx
│   └── LeagueTabs.tsx
├── team/
│   ├── FormBadge.tsx          # W/D/L badges last 5
│   └── TeamCard.tsx
└── ui/
    ├── LiveBadge.tsx          # pulsing green dot + "LIVE" text
    ├── ScoreBig.tsx           # large score display (DM Mono)
    └── StatLabel.tsx          # uppercase small label
```

---

## Docker Compose (Local)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: kickstat
      POSTGRES_USER: kickstat
      POSTGRES_PASSWORD: password

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on: [db, redis]
    ports: ["8000:8000"]

  celery:
    build: ./backend
    command: celery -A config worker -l info
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on: [db, redis]

  celery-beat:
    build: ./backend
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    depends_on: [db, redis]

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
    env_file: .env
    ports: ["3000:3000"]
```

---

## Build Order

Follow this sequence strictly. Do not skip phases.

### Step 1 — Django Foundation
1. Scaffold Django project with split settings
2. Create all models (leagues, matches, predictions apps)
3. Run migrations
4. Register all models in Django admin with search + filters
5. Confirm admin loads with `python manage.py createsuperuser`

### Step 2 — Sync Layer
1. Implement `sync/tasks/football_data.py`:
   - `sync_leagues()` — pull and upsert all covered leagues
   - `sync_standings(league_id)` — upsert standings
   - `sync_fixtures(league_id, days_ahead=7)` — upcoming fixtures
   - `sync_results(league_id)` — finished matches + stats
2. Implement `sync/tasks/api_football.py`:
   - `sync_liga1_fixtures()` — Liga 1 upcoming
   - `sync_liga1_results()` — Liga 1 results
3. Write management command `python manage.py initial_sync` — runs all sync tasks once sequentially for bootstrap

### Step 3 — DRF Endpoints
1. Build all endpoints listed in PRD
2. Add django-filter for `?league=&status=&date=` filtering
3. Test all endpoints with DRF browsable API

### Step 4 — Next.js Frontend
1. Setup Tailwind with Kickstat tokens
2. Build component library (bottom-up: ui → match → league → team)
3. Build pages in order: `/` → `/league/[slug]` → `/match/[id]` → `/predictions`

### Step 5 — ML Pipeline
1. Write StatsBomb ingestion management command
2. Implement `ml/features.py`
3. Train Phase 1 model with `ml/train.py`
4. Wire prediction Celery task
5. Build `PredictionDonut` component

---

## Key Decisions (Do Not Change)

- **No user auth in v1** — all endpoints public read-only
- **No real-time WebSocket** — polling every 60s is sufficient for free tier
- **Liga 1 via API-Football only** — do not try to get it from football-data.org
- **StatsBomb for xG** — do not use any paid xG source
- **`raw_data` JSONField is mandatory** on Match — allows reprocessing without re-fetching API
- **Predictions run at 08:00 WIB daily** — not on-demand per request

---

## Definition of Done (Phase 1–2)

- [ ] All models migrated and visible in admin
- [ ] Initial sync populates at least 3 leagues with fixtures + standings
- [ ] `/api/leagues/` returns data
- [ ] `/api/matches/live/` returns empty list (or live data on a matchday)
- [ ] `/api/matches/{id}/` returns full match detail
- [ ] Next.js home page shows today's fixtures
- [ ] Match card shows score, teams, status, league
- [ ] Standings table renders correctly for EPL
- [ ] Docker Compose `up` works cleanly from fresh clone
