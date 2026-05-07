# AI-Assisted Pre-Triage System for Pakistani Public Hospitals

This repository contains a starter implementation for a multi-agent, Retrieval-Augmented Generation (RAG) based pre-triage platform designed for public hospital workflows in Pakistan.

Primary language support is **Urdu**, with **English** as secondary.

## Project Overview

The system helps collect patient intake data, triage urgency, apply hard safety rules, route to departments, and provide patient-friendly explanation messages in Urdu. It includes a simple kiosk UI for intake and a staff dashboard for review and override.

## Features

- Voice/text intake simulation
- Mandatory field validation
- RAG-style protocol retrieval (simulated ChromaDB)
- AI triage urgency scoring (1-5)
- Hard safety rule overrides
- Department routing
- Urdu patient response generation
- Staff dashboard to view triage status and override
- Audit logging of decisions

## Tech Stack

- Frontend: React.js + Tailwind CSS (Vite)
- Backend: FastAPI + Pydantic
- AI Services: Modular Python agents
- Vector DB: ChromaDB (simulated)
- Database: PostgreSQL schema and seed script
- Workflow: n8n JSON workflow sample

## Folder Structure

```
docs/
frontend/
  kiosk-ui/
  staff-dashboard/
backend/
ai-services/
  intake-agent/
  triage-agent/
  rag/
  explanation-agent/
database/
integrations/
n8n-workflows/
scripts/
```

## Setup (Without Docker)

### 1) Clone and enter

```bash
git clone <your-repo-url>
cd PreTriage
```

### 2) Backend setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Run backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

### 3) Frontend setup (Kiosk)

```bash
cd frontend/kiosk-ui
npm install
npm run dev
```

### 4) Frontend setup (Staff Dashboard)

```bash
cd ../staff-dashboard
npm install
npm run dev
```

### 5) PostgreSQL schema

Apply SQL from:

```text
database/schema.sql
```

### 6) Seed data

```bash
python scripts/seed_data.py
```

## Notes for FYP Expansion

- Replace simulated RAG with real ChromaDB client and embeddings
- Add STT/TTS APIs for Urdu voice interaction
- Add authentication and RBAC for staff users
- Add background task queue and persistent event store
- Add analytics for triage trends and hospital load
