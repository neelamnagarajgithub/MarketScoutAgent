#!/bin/bash
# scripts/upload-secrets.sh
# Bulk upload all secrets to Cloudflare Workers from .secrets.json file

set -e  # Exit on error

ENV=${1:-production}
SECRETS_FILE=".secrets.json"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔐 Cloudflare Workers Secret Uploader${NC}"
echo "Environment: $ENV"
echo "Secrets file: $SECRETS_FILE"
echo ""

# Check if .secrets.json exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "${RED}❌ Error: $SECRETS_FILE not found${NC}"
    echo ""
    echo "Create a .secrets.json file with your secrets:"
    echo ""
    echo '{
  "SUPABASE_URL": "https://your-project.supabase.co",
  "SUPABASE_KEY": "your-anon-key",
  "DATABASE_URL": "postgresql://...",
  "SERPAPI": "your-serpapi-key",
  "NEWSAPI": "your-newsapi-key"
}'
    echo ""
    echo "⚠️  Remember: NEVER commit .secrets.json to git!"
    echo ""
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ Error: jq is not installed${NC}"
    echo "Install it with:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu: sudo apt-get install jq"
    echo "  Windows: choco install jq"
    exit 1
fi

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo -e "${RED}❌ Error: wrangler is not installed${NC}"
    echo "Install it with: npm install -g wrangler"
    exit 1
fi

# Count total secrets
TOTAL=$(jq '. | length' "$SECRETS_FILE")
echo -e "Found ${YELLOW}$TOTAL${NC} secrets to upload...\n"

# Upload each secret
SUCCESS=0
FAILED=0

jq -r 'to_entries | .[] | "\(.key) \(.value)"' "$SECRETS_FILE" | while read -r key value; do
    # Skip empty lines
    [ -z "$key" ] && continue
    
    echo -n "Uploading $key... "
    
    # Upload secret
    if echo "$value" | wrangler secret put "$key" --env "$ENV" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((SUCCESS++))
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
    fi
done

echo ""
echo -e "${GREEN}✓ Upload complete!${NC}"
echo ""
echo "Verify secrets were uploaded:"
echo "  wrangler secret list --env $ENV"
echo ""
echo "Deploy your worker:"
echo "  wrangler deploy --env $ENV"
echo ""
