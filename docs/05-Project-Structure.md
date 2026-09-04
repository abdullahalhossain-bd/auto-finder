# Project Structure

ai-sales-agent/
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── repositories/  # Data access
│   │   ├── services/      # Business logic
│   │   ├── workers/       # Celery tasks
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── hooks/
│   │   └── lib/
│   └── package.json
├── docs/                  # All project documentation
├── tests/
├── docker-compose.yml
└── README.md
