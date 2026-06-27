# Kickstat

Public-facing football analytics platform: live scores, match stats, league standings,
and AI match predictions for major European leagues + Indonesian Liga 1.

- **Backend:** Django 5 + DRF, Celery + Redis, PostgreSQL 16
- **Frontend:** Next.js 14 (App Router), Tailwind, Recharts
- **Data:** football-data.org (Europe), API-Football (Liga 1), StatsBomb (ML training)

See [PRD.md](PRD.md) and [CLAUDE.md](CLAUDE.md) for the full spec and conventions.

## Quick start (local)

```bash
cp .env.example .env        # fill in API keys
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py initial_sync
```

- Backend / admin: http://localhost:8000/admin
- API: http://localhost:8000/api/
- Frontend: http://localhost:3000

## Testing

Backend tests run against sqlite + in-memory cache with Celery eager — no
Postgres/Redis needed:

```bash
docker compose exec backend python manage.py test --settings=config.settings.test
# or locally (Python 3.12 venv):
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

Covers sync API-response parsing (mocked HTTP), all DRF endpoints, and the
ML train/predict/evaluate pipeline.

Frontend:

```bash
cd frontend && npm run lint && npm run build
```

## Layout

```
backend/   Django project (config + apps/ + ml/)
frontend/  Next.js app
nginx/     Reverse proxy config for production
```
