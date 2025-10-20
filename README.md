# Bike Tracker Alerts System — Clone & Run Guide (Neon-only)

This is a full‑stack MVP that ingests tracker alert emails (via Gmail IMAP), stores normalized alerts in Neon (PostgreSQL), and provides a React (CRA + Tailwind + shadcn/ui) dashboard with auth, filtering, bikes view, and admin user management.

Live preview (current deploy on Emergent)
- Frontend: https://alerttracker-3.preview.emergentagent.com
- Backend base: https://alerttracker-3.preview.emergentagent.com/api

Important: All backend endpoints are prefixed with /api. Frontend must use REACT_APP_BACKEND_URL + /api.


## 1) Project Structure
```
/app
├── backend/
│   ├── server.py              # FastAPI app (Neon-only)
│   ├── requirements.txt       # Python deps (asyncpg/FastAPI/etc.)
│   └── .env.example           # Backend env template
├── frontend/
│   ├── package.json           # CRA app
│   ├── .env.example           # Frontend env template
│   ├── craco.config.js        # Dev server config (port 3000)
│   └── src/
│       ├── App.js             # Main UI (dashboard, admin, bikes)
│       ├── index.js, index.css
│       └── components/ui/     # shadcn-like UI (table, card, popover, date-range, sonner)
└── README.md (this file)
```


## 2) Requirements
- Python 3.11+
- Node 18+ and Yarn 1.x
- Neon (PostgreSQL) database (SSL required)
- Optional: Gmail IMAP (email + app password) for ingest


## 3) Environment Variables
Create env files from the provided templates and fill in values.

Backend: backend/.env (copy from .env.example)
```
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@YOUR_NEON_HOST/neondb?sslmode=require
APP_ENV=development  # or production (forces secure cookies)
JWT_SECRET_KEY=your_long_random_secret

# Optional metadata for Stack Auth (not required for current login flow)
STACK_PROJECT_ID=96941442-1c79-4bdf-acbd-59ed08d16109
STACK_JWKS_URL=https://api.stack-auth.com/api/v1/projects/96941442-1c79-4bdf-acbd-59ed08d16109/.well-known/jwks.json
```

Frontend: frontend/.env (copy from .env.example)
```
# Backend base URL WITHOUT /api suffix
REACT_APP_BACKEND_URL=http://localhost:8001

# Optional metadata for Stack Auth (not required for current login flow)
REACT_APP_STACK_PROJECT_ID=96941442-1c79-4bdf-acbd-59ed08d16109
REACT_APP_STACK_PUBLISHABLE_CLIENT_KEY=pck_...
```

Notes
- Do not include /api in REACT_APP_BACKEND_URL. The UI appends /api automatically.
- In production with HTTPS and different origins, use APP_ENV=production and configure CORS if needed.


## 4) Local Development (one terminal per service)

Backend (FastAPI)
```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit values
uvicorn server:app --host 0.0.0.0 --port 8001
```

Frontend (CRA + Tailwind)
```
cd frontend
yarn install
cp .env.example .env  # set REACT_APP_BACKEND_URL to http://localhost:8001
yarn start
```

The frontend dev server runs on http://localhost:3000 and calls the backend at http://localhost:8001/api.


## 5) First Run & Seed User
- On backend startup, database schema is auto-created in Neon (no manual SQL needed).
- A default admin user is auto-seeded if not present:
  - username: admin
  - password: dimension
- Change the admin password in production.


## 6) Core Features
- Auth (cookie-based JWT, HttpOnly)
  - POST /api/auth/login with { username, password }
  - POST /api/auth/refresh (cookies)
  - POST /api/auth/logout (clear cookies)
- Alerts ingestion (Gmail IMAP)
  - POST /api/gmail/connect { email, app_password } (stores per-user credentials)
  - POST /api/sync/manual (processes recent emails)
  - POST /api/sync/progressive (lotes de 10)
  - POST /api/sync/today (força full scan de novos)
- Alerts API
  - GET /api/alerts/categories
  - GET /api/alerts/list?category=&page=&limit=&start_date=&end_date=
    - created_at é retornado (ISO). Frontend usa filtro de data (Date Range em popover). Limit padrão alto no backend; frontend usa 5000.
  - DELETE /api/alerts/{id}
  - POST /api/alerts/{id}/acknowledge
  - POST /api/alerts/{id}/status
  - POST /api/alerts/{id}/notes
  - POST /api/alerts/{id}/assign
  - POST /api/alerts/{id}/favorite
  - GET /api/alerts/export (CSV)
- Bikes & Notas
  - GET /api/bikes/list (otimizado; calcula alert_count e notes_count)
  - GET /api/bikes/{bike_id}/history (últimos 50 alerts + notas)
  - POST /api/bikes/{bike_id}/notes
  - PUT /api/bikes/notes/{note_id}
  - DELETE /api/bikes/notes/{note_id}
- Admin (usuários)
  - GET /api/users/list (admin)
  - POST /api/users/create (admin)
  - PUT /api/users/{id} (admin)
  - DELETE /api/users/{id} (admin)


## 7) UI Highlights
- Dashboard de alertas
  - Tabela (shadcn/ui Table), cards (shadcn/ui Card), filtro de data com popover (DateRangePicker)
  - Ordenação, busca por dispositivo, badges de severidade
  - Limite de carregamento alto (5000) — não há botão “Load More”
- Bikes
  - Cards por bike com contagem de alertas e notas; modal de histórico; notas CRUD
- Admin
  - CRUD de usuários (roles: admin/viewer)
- Dark Mode
  - Toggle salvo em localStorage (sem dependência de next-themes)


## 8) Deployment (exemplo)

Backend (Render/Heroku/Fly)
- Defina variáveis:
  - DATABASE_URL (Neon, com sslmode=require)
  - APP_ENV=production
  - JWT_SECRET_KEY=chave_forte
- Execute com `uvicorn server:app --host 0.0.0.0 --port 8001`
- Se frontend estiver em outro domínio, habilite CORS na API (ver Troubleshooting)

Frontend (Vercel/Netlify)
- Configure REACT_APP_BACKEND_URL para a URL pública do backend (sem /api)
- Build com `yarn build`

Neon
- Use a connection string com pooler e SSL: `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`


## 9) Troubleshooting
- Login não mantém sessão
  - Em produção (HTTPS), APP_ENV=production (secure cookies, samesite=none)
  - Se front/back em domínios diferentes, configure CORS no backend
- Só aparecem 200 alertas
  - Certifique-se de estar usando limit alto (o frontend usa 5000). O backend aceita limites altos.
- Gmail IMAP falha
  - Verifique e-mail/app password válidos e 2FA habilitado. O endpoint retorna 400 com mensagem em credenciais inválidas.

Habilitar CORS (se necessário)
- Adicione no server.py (exemplo):
```
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["https://seu-front.example.com"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)
```


## 10) Segurança & Boas práticas
- Nunca commitar .env (use os .env.example como referência)
- Trocar senha do admin em produção
- JWT_SECRET_KEY forte/estável
- Limitar origins em CORS
- Usar SSL no Neon (sslmode=require)


## 11) Scripts úteis
- Backend dev (local): `uvicorn server:app --host 0.0.0.0 --port 8001`
- Frontend dev (local): `yarn start`
- Build front: `yarn build`


## 12) Suporte
Se precisar de orientação para deploy (Render/Heroku/Fly/Vercel) ou ativar filtro de datas diretamente no backend (enviar start_date/end_date), abra uma issue ou solicite no chat do projeto.
