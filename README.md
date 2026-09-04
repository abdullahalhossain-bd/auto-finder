# AI Sales Agent for Local Businesses

**Stage 1: Local Business Opportunity Finder + Safe Outreach Assistant**

Find local businesses that need websites or online booking systems and help freelancers & small agencies reach them safely with personalized outreach.

## Current Status: Stage 1 Core Complete

### What works now
- Auth (Register / Login / JWT)
- Organizations & Memberships
- Campaign creation with Natural Language parsing
- Business Discovery (OpenStreetMap / Overpass)
- Deterministic Website Analysis
- Rule-based Opportunity Scoring
- Confidence states (Verified / Likely / Unknown / Not Found)
- Lead management + Pipeline stages
- Message generation + **Mandatory Human Approval** queue
- Suppression / Do Not Contact list
- Full API under `/api/v1`

### Safety rules enforced
- No automatic email sending
- Human approval required before any send
- Suppression list checked before send
- Contact Found ≠ Consent to Contact
- LLM never decides Opportunity Score

## Tech Stack
- Python 3.11+ / FastAPI / SQLAlchemy 2 / Alembic
- PostgreSQL + Redis
- Celery (workers ready)
- Ollama (local LLM)
- React + TypeScript frontend (structure ready)

## Quick Start

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment
cp ../.env.example ../.env
# Edit .env with your APP_SECRET_KEY and DATABASE_URL

# 4. Migrate
cd ..
alembic upgrade head

# 5. Run API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## Project Structure
```
ai-sales-agent/
├── backend/app/
│   ├── api/          # Auth, Campaigns, Leads, Messages, Suppression
│   ├── models/       # All Stage 1 tables
│   ├── schemas/      # Pydantic models
│   ├── repositories/ # Data access
│   ├── services/     # Business logic (Discovery, Scoring, LLM, NL Parser)
│   ├── workers/      # Celery tasks
│   └── core/         # Config, security, database
├── docs/             # Full product & technical specs
├── frontend/         # React app (starter)
├── alembic/          # Migrations
└── tests/
```

## Documentation
See `/docs` folder for complete Product Spec, Architecture, Features, UI Pages, Coding Rules, and Roadmap.

## Next Phases
- Phase 2: Better website intelligence + more signals
- Phase 3: Full Ollama/Groq personalization polish
- Phase 4: ESP integration (Resend/Postmark) + real sending after approval
- Phase 5: Frontend complete + closed beta

## License
Private — All rights reserved
