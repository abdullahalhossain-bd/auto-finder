# Production readiness checklist

## Secrets (never commit real values)
Generate and store in your host secret manager (not git):

```bash
# App
openssl rand -hex 32          # → APP_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → CREDENTIAL_ENCRYPTION_KEY

# Database / Redis — managed services with TLS
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/ai_sales_agent
REDIS_URL=rediss://...

# ESP (use sandbox until go-live)
ESP_PROVIDER=resend|smtp|console
ESP_API_KEY=...

# Optional
GOOGLE_PLACES_API_KEY=...     # only if GOOGLE_PLACES_ENABLED=true
STRIPE_SECRET_KEY=...         # when billing is enabled
SENTRY_DSN=...
```

Set `APP_ENV=production`. Confirm `.env` is not in the image layer or repo.

## Must be green before public traffic
- [ ] `alembic upgrade head` on production DB
- [ ] HTTPS termination (reverse proxy) + `PUBLIC_APP_URL=https://...`
- [ ] `ALLOWED_ORIGINS` locked to real frontend origin(s)
- [ ] Celery worker(s) running with same env as API
- [ ] Redis durable / managed
- [ ] Rate limiting on (default on); consider Redis-backed limiter multi-node
- [ ] ESP domain / SPF / DKIM verified per org (sending_identities)
- [ ] Privacy Policy + Terms linked from register (`/api/v1/legal/*`)
- [ ] Backup + restore tested for Postgres
- [ ] Log aggregation (JSON stdout → your log stack); optional Sentry

## Volume caps (server-enforced)
| Plan    | Campaigns / month | Leads / month |
|---------|-------------------|---------------|
| trial   | 1                 | 25            |
| starter | 10                | 500           |
| pro     | 50                | 5000          |

Send path also enforces daily/weekly ESP caps from env.

## Tests to run in CI
```bash
cd backend && pytest -q ../../tests/test_dedupe.py ../../tests/test_scoring.py ../../tests/test_esp_unsubscribe.py ../../tests/test_plan_limits.py
# Full suite (needs Postgres test DB):
pytest -q ../../tests
```

## Explicitly still Stage-1 limited
Billing Stripe webhooks, full sending-identity UI, and multi-node rate-limit store are partially specified — complete before charging cards at scale.
