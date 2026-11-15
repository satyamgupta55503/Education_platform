# Vidyayantra OS — Education Platform

An AI-powered education platform monorepo containing multiple apps and services.

## Project Structure

```
Vidyayantra_OS/
├── admin-dashboard/      # Next.js 15 admin panel (port 3002)
├── school-dashboard/     # Next.js 15 school panel (port 3001)
├── educat_backend/       # FastAPI + Python AI/ML backend
└── educat_flutter/       # Flutter mobile app
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Admin / School UI | Next.js 15, TypeScript, Tailwind CSS, Recharts |
| Backend API | FastAPI, Python, Supabase, Redis, Celery |
| AI / LLM | LangChain, Google Gemini, OpenAI |
| Auth | Firebase Admin, python-jose, JWT |
| Mobile | Flutter / Dart |
| Database | Supabase (PostgreSQL) |
| Cache | Redis |
| Payments | Razorpay |
| Infra | Docker, Railway |

## Getting Started

### Admin Dashboard
```bash
cd admin-dashboard
npm install
cp .env.local.template .env.local   # fill in your values
npm run dev   # runs on http://localhost:3002
```

### School Dashboard
```bash
cd school-dashboard
npm install
cp .env.local.template .env.local
npm run dev   # runs on http://localhost:3001
```

### Backend (FastAPI)
```bash
cd educat_backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env       # fill in your values
uvicorn app.main:app --reload
```

### Flutter App
```bash
cd educat_flutter
flutter pub get
flutter run
```

### Docker (Full Stack)
```bash
cd educat_backend
docker-compose up --build
```

## Environment Variables

Each sub-project has its own `.env.example` / `.env.local.template` — copy and fill before running.

> ⚠️ Never commit real `.env` files or credential JSON files to this repo.

## License

Private — All rights reserved.
