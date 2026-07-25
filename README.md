---
title: Frontend Pathnovo
emoji: 📐
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.38.0"
python_version: "3.12"
app_file: app.py
pinned: false
---

# Document Delta Engine & Grounded Chat — Frontend

A thin Streamlit client for the Document Delta & Grounded Chat backend API.
This app holds **no pipeline code and no API keys** — it only calls a deployed
backend over HTTP (file upload / JSON), renders the results, and streams a
grounded chat session. The backend (ingestion, delta engine, RAG chat,
observability) lives in the sibling `Pathnovo Assessment` repo and is deployed
separately (see that repo's `AWS_DEPLOY.md`).

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set API_BASE_URL to your backend (defaults to http://localhost:8000)

streamlit run app.py
```

Opens at `http://localhost:8501`. Point it at a locally running backend
(`make api` in the backend repo) or a deployed one via the sidebar's
"API base URL" field.

## What it does

1. Pick a bundled sample pair or upload two PDFs — sent to the backend's
   `POST /delta`.
2. Shows the delta summary, full delta table, redline overlay (rendered
   server-side as PNGs so this app needs no PDF library), and downloadable
   Markdown/JSON reports.
3. Grounded chat (`POST /chat`) with `[PID A, Page X]` / `[Delta Report, Item
   #N]` citations, streamed per session.
4. An "Observability" tab showing per-stage latency and LLM token/cost
   telemetry for the current session (`GET /trace/{session_id}`).

## Deployment

See `DEPLOY.md` for deploying this app to Hugging Face Spaces. It only needs
the backend's public URL (and an API token if the backend requires one) — set
both as Space secrets/variables or type them into the sidebar.
