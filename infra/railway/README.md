# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt && pip install -r requirements-ml.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

> **ML deps & memory:** `requirements-ml.txt` (rembg + onnxruntime) is large and the first
> cutout downloads the selected U²-Net model (~176 MB for `u2net`) to `~/.u2net/` at runtime.
> Give the API service enough memory and ephemeral disk, and expect a slower first request as
> the model downloads. This is a **CPU** deployment (no GPU on Railway); leave `REMBG_PROVIDERS`
> unset so it defaults to CPU. If you only want to demo ingest/browse without removal, you can
> skip `requirements-ml.txt` — removal endpoints will return a clean 503.

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your bucket region, e.g. `us-west-004` (endpoint is derived) |
| `B2_PUBLIC_URL_BASE` | *Optional* — public/CDN base URL; presigned URLs work without it |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
