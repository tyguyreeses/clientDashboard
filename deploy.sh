#!/usr/bin/env bash
set -e

cd /srv/client-dashboard

git pull --ff-only origin main

.venv/bin/pip install -e .

cd frontend
npm ci
npm run build
cd ..

set -a
source /etc/client-dashboard.env
set +a

PYTHONPATH=src .venv/bin/alembic upgrade head

sudo systemctl restart client-dashboard
sudo systemctl status client-dashboard --no-pager