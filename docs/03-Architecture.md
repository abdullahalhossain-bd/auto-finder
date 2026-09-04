# High Level Architecture

Frontend (React + TypeScript + Tailwind)
        ↓
FastAPI Backend (Auth, Campaigns, Leads, Approval, CRM)
        ↓
PostgreSQL  ←→  Redis
        ↓
Celery Workers:
  - Discovery Worker
  - Website Analysis Worker
  - Scoring Worker
  - LLM Personalization Worker
  - Outreach Worker (ONLY after Human Approval)

Key Rules:
- Every query scoped by organization_id
- Suppression list checked before every send
- No automatic sending path exists
- Confidence state on important fields
- Scraped content treated as untrusted
