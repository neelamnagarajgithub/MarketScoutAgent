# Deploy FastAPI Backend to Cloud

## Quick Start

### Option 1: Google Cloud Run (Recommended)
```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="us-central1"
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Railway.app (Easiest)
1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Deploy from `railway.toml` automatically
4. Add environment variables in dashboard

### Option 3: Render.com
1. Go to [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Deploy using `render.yaml`

---

## Detailed Setup: Google Cloud Run

### 1. Prerequisites
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Install Docker
# Mac: brew install docker
# Linux: sudo apt-get install docker.io

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Create Service Account
```bash
gcloud iam service-accounts create market-scout-api \
  --display-name="Market Scout API Service"

# Grant Cloud Run admin role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:market-scout-api@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin
```

### 3. Set Secrets / Environment Variables
```bash
# Create secrets in Google Secret Manager
gcloud secrets create DB_URL --data-file=- <<< "postgresql://..."
gcloud secrets create GOOGLE_API_KEY --data-file=- <<< "your-key"
gcloud secrets create SUPABASE_URL --data-file=- <<< "https://xxx.supabase.co"
gcloud secrets create SUPABASE_KEY --data-file=- <<< "your-supabase-key"

# Grant service account access
for secret in DB_URL GOOGLE_API_KEY SUPABASE_URL SUPABASE_KEY; do
  gcloud secrets add-iam-policy-binding $secret \
    --member=serviceAccount:market-scout-api@PROJECT_ID.iam.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor
done
```

### 4. Deploy
```bash
./deploy.sh
```

### 5. Monitor
```bash
# View logs
gcloud run logs read market-scout-api --platform=managed --region=us-central1

# View metrics
gcloud monitoring dashboards list

# Test endpoint
curl https://market-scout-api-xxx.run.app/health
curl https://market-scout-api-xxx.run.app/docs
```

---

## Environment Variables

Create `.env` file locally (DO NOT commit):
```env
ENVIRONMENT=production
LOG_LEVEL=info
DATABASE_URL=postgresql://user:pass@host:5432/dbname
GOOGLE_API_KEY=your-google-api-key
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
```

---

## Cost Estimates

| Platform | Compute | Storage | Monthly Cost |
|----------|---------|---------|--------------|
| Cloud Run | 2 vCPU, 2GB RAM | Cloud SQL | ~$30-100 |
| Railway | Shared resources | PostgreSQL | ~$10-50 |
| Render | Shared / Dedicated | PostgreSQL | ~$7-100 |

---

## CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
      - run: gcloud builds submit --config cloudbuild.yaml
```

---

## Health Monitoring

- Health endpoint: `GET /health`
- Metrics: `/docs` (Swagger UI)
- Logs: GCP Cloud Logging, Railway/Render dashboards

---

## Troubleshooting

### Cold start taking too long
- Increase `min_instances` in `cloud_run.yaml` to keep 1 instance warm
- Use `memory: 2Gi` for faster Python startup

### Out of memory
- Increase `--memory` flag in deploy.sh
- Reduce concurrent requests via rate limiting

### API timeouts
- Increase `--timeout=3600` for long-running analyses
- Use async queue (Celery + Redis) for batch jobs

---

## Next Steps

1. ✅ Deploy backend with chosen platform
2. 📝 Set environment variables for each API key
3. 🧪 Test with: `curl SERVICE_URL/health`
4. 📊 Monitor logs and set up alerts
5. 🔄 Set up CI/CD for auto-deployment on git push
