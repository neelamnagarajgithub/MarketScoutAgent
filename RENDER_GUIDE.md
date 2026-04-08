# Render Deployment Guide

## What is Render?

Render is a simple, Python-friendly cloud platform perfect for deploying FastAPI backends. It handles:
- ✅ Automatic deployments from GitHub
- ✅ Built-in PostgreSQL databases
- ✅ Environment variables & secrets management
- ✅ Free tier available
- ✅ Auto-scaling

---

## Prerequisites

1. **Render Account** at [render.com](https://render.com)
2. **GitHub account** with this repo
3. **Config.yaml** with your API keys (private, not in git)

---

## Step 1: Prepare Repository

```bash
# Add config.yaml to .gitignore (if not already)
echo "config.yaml" >> .gitignore

# Create config template (without secrets)
cp config.yaml config.example.yaml
# Edit config.example.yaml and remove all real API keys

git add .gitignore config.example.yaml
git commit -m "Add config template, ignore secrets"
git push
```

---

## Step 2: Create Render Service

1. Go to [render.com](https://render.com) → New → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `market-scout-api`
   - **Root Directory**: Leave blank (uses root)
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8080`
   - **Plan**: Free tier or Starter (recommended)

---

## Step 3: Set Environment Variables

In **Render Dashboard → Your Service → Settings → Environment**

Add each API key:
```
DATABASE_PROVIDER=supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
DATABASE_URL=postgresql://...
SERPAPI_API_KEY=5d0391cc...
GOOGLE_API_KEY=AIzaSyBYe...
NEWSAPI_KEY=11fd5cc8...
(and all others from config.yaml)
```

---

## Step 4: Upload config.yaml

### Option A: As Environment Variable (Easiest)

```bash
# In Render dashboard, add as multi-line env var:
# Name: CONFIG_FILE_CONTENT
# Value: [paste entire config.yaml content]
```

Then create a startup script that creates the file:

```bash
#!/bin/bash
echo "$CONFIG_FILE_CONTENT" > config.yaml
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Save as `start.sh` and update build command to `chmod +x start.sh && ./start.sh`

### Option B: Create in Private GitHub Repo (More Secure)

1. Create private repo: `github.com/yourname/marketscout-secrets`
2. Push config.yaml there
3. Create GitHub Personal Access Token (Settings → Developer Settings → Personal Access Tokens)
4. In Render, add:
   ```
   GITHUB_PAT=ghp_xxxxxxxxxxxx
   SECRETS_REPO=yourname/marketscout-secrets
   ```
5. Create `fetch-config.sh`:
```bash
#!/bin/bash
git clone "https://$GITHUB_PAT@github.com/$SECRETS_REPO.git" secrets
cp secrets/config.yaml ./
rm -rf secrets
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

## Step 5: Deploy

Once environment variables are set:

1. Click **Deploy** button in Render dashboard
2. Watch build logs
3. Service starts automatically
4. You get a URL: `https://market-scout-api-xxxxx.onrender.com`

---

## Step 6: Test Deployment

```bash
SERVICE_URL="https://market-scout-api-xxxxx.onrender.com"

# Health check
curl $SERVICE_URL/health

# View API docs
open $SERVICE_URL/docs

# Make API call
curl -X POST $SERVICE_URL/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "market trends"}'
```

---

## Step 7: Setup Auto-Deploys

In **Render Dashboard → Settings → Auto-Deploy**:
- ✅ Check "Auto-deploy from GitHub"
- ✅ Select branch: `main`

Now every `git push` to main = automatic deployment!

```bash
git add .
git commit -m "Update feature"
git push  # Render auto-deploys
```

---

## Managing Secrets

### Update config.yaml

```bash
# If using Option A (env var method)
1. Edit config.yaml locally
2. Copy entire file content
3. Paste into CONFIG_FILE_CONTENT env var in Render dashboard
4. Click "Save Changes" → Render redeploys

# If using Option B (private repo method)
git push to your private secrets repo
Render automatically pulls and rebuilds
```

### Add new API keys

1. Get new API key
2. Add to config.yaml locally
3. Update either:
   - CONFIG_FILE_CONTENT env var (Option A)
   - Push to secrets repo (Option B)
4. Render redeploys

---

## Monitoring

```bash
# View logs in Render Dashboard
# Or via CLI:
# Settings → Logs tab
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check logs, ensure `requirements.txt` is correct |
| Module not found | Missing dependency - add to `requirements.txt` |
| config.yaml not found | Verify CONFIG_FILE_CONTENT or secrets repo is accessible |
| Timeout errors | Increase from Render dashboard settings |
| "Application failed to start" | Check logs, verify all env vars are set |

---

## Pricing

| Plan | Monthly Cost | Concurrent Processes |
|------|--------------|---------------------|
| Free | $0 | 1 (sleeps after 15 min) |
| Starter | $7 | 1 (always on) |
| Standard | $25+ | 2-3 (auto-scaling) |

---

## Custom Domain

1. Go to **Settings → Custom Domain**
2. Enter your domain: `api.yourdomain.com`
3. Update DNS records (Render provides instructions)
4. Access at: `https://api.yourdomain.com`

---

## Database Setup (Optional)

Add PostgreSQL in Render:

1. **New → PostgreSQL**
2. Name: `marketscout-db`
3. Render creates connection string automatically
4. Add to environment: `DATABASE_URL=postgresql://...`

---

## Quick Redeploy

```bash
# After making code changes
git add .
git commit -m "Update"
git push  # Auto-deploys to Render
```

Or manually redeploy in Render dashboard → "Deploy latest commit"

---

## Performance Tips

1. **Use free tier for testing**, upgrade if high traffic
2. **Keep cold start fast**: ~5-10 seconds normal
3. **Database queries**: Use Supabase for better performance
4. **Caching**: Use Redis add-on if needed

---

## Next Steps

1. ✅ Create Render account & connect GitHub
2. ✅ Set all environment variables
3. ✅ Upload config.yaml (Option A or B)
4. ✅ Deploy & test
5. ✅ Setup custom domain (optional)
6. ✅ Monitor logs
