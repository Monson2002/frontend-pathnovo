# Deploying to Hugging Face Spaces

This app is a thin API client — it needs no system packages (no tesseract,
no PDF libs) since all document processing happens on the backend. Deployment
is just pushing this directory to a Space.

## Prerequisites

Deploy the backend first (see `../Pathnovo Assessment/AWS_DEPLOY.md`) and note
its public URL, e.g. `https://xxxx.us-east-1.awsapprunner.com`, plus its
`API_AUTH_TOKEN` if one is set.

## 1. Create the Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Space name**: e.g. `frontend-pathnovo`
   - **Hardware**: CPU basic is enough — this app makes HTTP calls only
   - **Visibility**: your choice
3. Click **Create Space**.

The `README.md` here already has the required Spaces YAML frontmatter
(`sdk: streamlit`, `app_file: app.py`) — don't remove it.

## 2. Set variables

In the Space's **Settings → Variables and secrets**:

| Name | Type | Value |
|---|---|---|
| `API_BASE_URL` | Variable | Your deployed backend's URL |
| `API_AUTH_TOKEN` | Secret (optional) | Only if the backend requires it — users can also type this into the sidebar instead |

## 3. Push this directory

```bash
cd "Pathnovo Assessment - Frontend"
git init                # if not already a git repo
git add .
git commit -m "Thin Streamlit client for the delta + grounded chat API"
git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
git push space main
```

Spaces builds automatically on push: installs `requirements.txt`, then runs
`streamlit run app.py`.

## 4. Verify

Open the Space URL. The sidebar should show "Backend reachable." (green).
Pick a bundled sample pair, click **Compute Delta**, and confirm the delta
table, redline overlay, and a real grounded chat answer with citations all
come back from the backend.

## Notes

- **CORS**: the backend's `API_CORS_ORIGINS` must include this Space's URL
  (or be left as `*` for a quick demo) or the browser will block the calls —
  see the backend's `AWS_DEPLOY.md`.
- **No secrets live here**: this app never holds `NVIDIA_API_KEY` — that stays
  server-side on the backend, which is the point of splitting frontend/backend
  this way.
