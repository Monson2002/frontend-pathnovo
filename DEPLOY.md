# Deploying to Streamlit Community Cloud

This app is a thin API client — it needs no system packages (no tesseract,
no PDF libs) since all document processing happens on the backend. Deployment
is just connecting this GitHub repo to Streamlit Community Cloud.

## Prerequisites

Deploy the backend first (see `../Pathnovo Assessment/AWS_DEPLOY.md`) and note
its public URL, e.g. `https://xxxx.us-east-1.awsapprunner.com`, plus its
`API_AUTH_TOKEN` if one is set.

## 1. Push this repo to GitHub

Streamlit Community Cloud deploys from a GitHub repo (not git-push-to-deploy
like Hugging Face Spaces):

```bash
cd "Pathnovo Assessment - Frontend"
gh repo create <your-username>/frontend-pathnovo --public --source=. --push
# or manually: create an empty repo on github.com, then
#   git remote add origin https://github.com/<your-username>/frontend-pathnovo
#   git push -u origin main
```

## 2. Create the app on Streamlit Community Cloud

1. Go to https://share.streamlit.io → **New app**
2. Pick the GitHub repo you just pushed, branch `main`, main file path `app.py`
3. Under **Advanced settings → Secrets**, add:
   ```toml
   API_BASE_URL = "https://your-backend-url"
   ```
   (`app.py` reads this via `st.secrets` first, falling back to the
   `API_BASE_URL` env var, then `http://localhost:8000`.)
4. Click **Deploy**.

Streamlit Cloud installs dependencies from `pyproject.toml`/`uv.lock`
automatically (no `requirements.txt` needed) and runs `streamlit run app.py`
for you — free tier, no card required.

## 3. Verify

Open the app URL Streamlit Cloud gives you. The sidebar should show "Backend
reachable." (green). Pick a bundled sample pair, click **Compute Delta**, and
confirm the delta table, redline overlay, and a real grounded chat answer with
citations all come back from the backend.

## Notes

- **CORS**: the backend's `API_CORS_ORIGINS` must include your Streamlit
  Cloud app's URL (or be left as `*` for a quick demo) or the browser will
  block the calls — see the backend's `AWS_DEPLOY.md`.
- **No secrets live here**: this app never holds `NVIDIA_API_KEY` — that stays
  server-side on the backend, which is the point of splitting frontend/backend
  this way.
- **API token in the sidebar**: if the backend has `API_AUTH_TOKEN` set,
  visitors type it into the sidebar's "API token" field per-session — it's
  never stored in this repo.

## Alternative: Hugging Face Spaces

A Space (`monson2002/frontend-pathnovo`) already exists with the same app —
see git remote `space`. It requires a paid HF plan for `cpu-basic` hardware on
this account, which is why Streamlit Community Cloud is the primary path here.
If that changes, `git push space main` deploys the identical code there too
(same README frontmatter already declares `sdk: streamlit`).
