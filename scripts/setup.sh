#!/usr/bin/env bash
set -e

echo "[1/4] Creating Python virtual environment"
python -m venv .venv

echo "[2/4] Activating environment and installing backend dependencies"
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "[3/4] Installing kiosk UI dependencies"
cd frontend/kiosk-ui
npm install

echo "[4/4] Installing staff dashboard dependencies"
cd ../staff-dashboard
npm install

echo "Setup complete."
echo "Run backend: uvicorn backend.main:app --reload --port 8000"
echo "Run kiosk UI: cd frontend/kiosk-ui && npm run dev"
echo "Run dashboard: cd frontend/staff-dashboard && npm run dev"
