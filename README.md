## JobPulse IR

Production-style intelligent recruitment + labor-market intelligence platform.

### Local development (Docker)

1) Copy environment file.

```bash
cp .env.example .env
```

2) Start Postgres + backend + frontend.

```bash
docker compose up --build
```

3) Open:

- Frontend: `http://localhost:3000`
- Backend API docs (Swagger): `http://localhost:8000/docs`

### Repo structure

- `frontend/`: Next.js + Tailwind + (later) shadcn/ui
- `backend/`: FastAPI + Postgres + FAISS (local vector search)
- `infra/`: docker, configs (crawler sources, etc.)
