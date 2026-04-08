# Render Port Binding Error - Fix Guide

## Problem

Render is not detecting any open ports. Error message:
```
No open ports detected, continuing to scan...
Port scan timeout reached, no open ports detected. 
Bind your service to at least one port.
```

## Root Cause

The `startCommand` in `render.yaml` was using `$PORT` environment variable, but Render requires a **hardcoded port number** in the start command.

## Solution

✅ **Fixed in render.yaml:**
```yaml
startCommand: "uvicorn app.main:app --host 0.0.0.0 --port 8080"
```

❌ **Was:**
```yaml
startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

---

## Steps to Redeploy

### 1. Verify render.yaml is Updated

Check that `render.yaml` has:
```yaml
startCommand: "uvicorn app.main:app --host 0.0.0.0 --port 8080"
healthCheckPath: /health
```

### 2. Push Changes to GitHub

```bash
git add render.yaml
git commit -m "Fix port binding for Render"
git push
```

### 3. Redeploy in Render Dashboard

1. Go to **Render Dashboard → Your Service**
2. Click **"Manual Deploy"** or **"Deploy latest commit"**
3. Wait for build (usually 2-3 minutes)
4. Watch the logs for `Application is running...`

### 4. Verify Deployment

Once deployed, test:

```bash
SERVICE_URL="https://market-scout-api-xxxxx.onrender.com"

# Health check (should return 200)
curl $SERVICE_URL/health

# If successful, you'll see:
# {"status": "healthy"}
```

---

## Why This Works

| Component | What It Does |
|-----------|-------------|
| `uvicorn` | ASGI server (like nginx for Python) |
| `app.main:app` | Points to FastAPI app in `app/main.py` |
| `--host 0.0.0.0` | Listen on all network interfaces |
| `--port 8080` | **Required:** Hardcoded port (Render scans this) |
| `healthCheckPath: /health` | Render pings `localhost:8080/health` to verify |

---

## Environment Variables in Render

Make sure these are set in **Render Dashboard → Settings → Environment**:

```
# Required for app to run
ENVIRONMENT=production
PYTHONUNBUFFERED=true
PORT=8080

# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...

# APIs
GOOGLE_API_KEY=AIzaSy...
SERPAPI_API_KEY=5d0391...
NEWSAPI_KEY=11fd5cc...
# ... other keys from config.yaml
```

---

## Troubleshooting

### Still getting "No open ports" error?

```bash
# 1. Check Dockerfile is correct
cat Dockerfile | grep -A 5 "EXPOSE\|CMD"

# Should show:
# EXPOSE 8080
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

# 2. Check render.yaml
cat render.yaml | grep -A 2 "startCommand"

# Should show:
# startCommand: "uvicorn app.main:app --host 0.0.0.0 --port 8080"

# 3. Check Render logs for startup errors
# Go to Render Dashboard → Logs tab
```

### Service builds but crashes?

1. Check logs in **Render Dashboard → Logs**
2. Look for errors like:
   - `ModuleNotFoundError` → Missing dependency in `requirements.txt`
   - `config.yaml not found` → Add via environment variable
   - `Connection refused` → Database credentials wrong

### Application times out on startup?

- Increase build timeout in Render dashboard
- Or add `startupTimeout: 600` to render.yaml (from existing fix)

---

## Commands for Quick Reference

```bash
# Test locally first (BEFORE pushing)
docker build -t market-scout:test .
docker run -p 8080:8080 market-scout:test

# Then push and deploy
git add .
git commit -m "Fix port binding"
git push  # Render auto-deploys if autoDeploy: true in render.yaml
```

---

## Monitoring After Fix

### View Real-Time Logs
```bash
# In Render Dashboard → Logs tab (live view)
# Or use Render CLI:
# render logs market-scout-api --follow
```

### Check Status
```bash
curl https://market-scout-api-xxxxx.onrender.com/health
# Returns: {"status":"healthy"}
```

### Monitor Uptime
- Render Dashboard shows deployment status
- Check metrics in **Settings → Metrics** tab

---

## Next Steps

1. ✅ Push updated `render.yaml` to GitHub
2. ✅ Trigger manual deploy in Render
3. ✅ Monitor logs during build
4. ✅ Test `/health` endpoint
5. ✅ If successful, your API is live!

---

**You're all set!** The port binding issue is now fixed. 🚀
