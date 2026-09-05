# AI Sales Agent for Local Businesses

**Stage 1 — Local Business Opportunity Finder + Safe Outreach Assistant**

Find local businesses that may need better websites or online booking and help freelancers and small agencies research, qualify, personalize, and safely prepare outreach.

## Current status

The Stage 1 core is implemented with production-oriented safety controls and CI coverage.

### Working capabilities
- JWT authentication, organizations, memberships, invites, password reset
- Natural-language campaign creation and structured campaign parameters
- OpenStreetMap / Overpass discovery with optional Google Places enrichment
- Strong business deduplication and organization isolation
- Deterministic Website Intelligence: mobile readiness, HTTPS, SEO, CTA, contact, booking, CMS, analytics, social and quality signals
- Rule-based Opportunity Scoring with stable score tiers
- Lead management, pipeline stages, disqualification and suppression / Do Not Contact
- AI-assisted message generation with mandatory human approval
- Safe outbound path with send-time subscription, identity, suppression, unsubscribe and volume-cap checks
- Database row locking to prevent concurrent duplicate sends for the same approved message
- Free/trial lead quota: **25 leads per rolling 24 hours**
- Concurrent discovery quota protection using PostgreSQL transaction-scoped advisory locks
- Live usage API with quota window and reset metadata
- Liveness and database/Redis readiness health endpoints
- Production configuration validation for secrets, public URL and CORS
- Frontend production build verified in GitHub Actions

## Safety rules

- No automatic outreach without human approval.
- Suppression is re-checked immediately before send.
- Contact found does not imply consent to contact.
- Opportunity Score is deterministic; the LLM does not control qualification.
- Sending requires a verified sending identity and active subscription/trial.
- Daily and weekly organization send caps are enforced server-side.

## Tech stack

- Python 3.11+ / FastAPI / SQLAlchemy 2 / Alembic
- PostgreSQL + Redis
- Celery workers + retry policy
- Ollama / remote OpenAI-compatible LLM gateway
- React + TypeScript + Vite + Tailwind
- Stripe billing integration

## Local development

```bash
docker compose up -d db redis

cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cd ..
# Copy .env.example to .env and set APP_SECRET_KEY + DATABASE_URL
alembic upgrade head

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend separately:

```bash
cd frontend
npm ci
npm run dev
```

API docs: `http://localhost:8000/docs`

Health: `http://localhost:8000/health`

Readiness: `http://localhost:8000/health/ready`

## Project structure

```text
ai-sales-agent/
├── backend/app/
│   ├── api/          # Auth, campaigns, leads, billing, outreach, etc.
│   ├── models/       # PostgreSQL data model
│   ├── schemas/      # Pydantic request/response schemas
│   ├── repositories/ # Data access
│   ├── services/     # Discovery, intelligence, scoring, LLM, billing, outreach
│   ├── workers/      # Celery tasks
│   └── core/         # Config, security, database, logging
├── frontend/         # React + TypeScript application
├── alembic/          # Database migrations
├── docs/             # Product, architecture, UI and roadmap documentation
└── tests/            # Automated regression tests
```

## CI

GitHub Actions runs:

1. Backend unit/regression tests without external services.
2. Frontend TypeScript typecheck + production build.

A separate integration environment with PostgreSQL/Redis should be used before enabling real outbound email in production.

## Next production-hardening milestones

- PostgreSQL integration/concurrency test suite in CI
- Stronger discovery cancellation checks and job-state observability
- Production ESP verification (SPF/DKIM), bounce/complaint processing and webhook monitoring
- End-to-end staging test: signup → campaign → discovery → lead intelligence → message → approval → safe send
- Production deployment, backups, monitoring and rollback runbook

## License

Private — All rights reserved
