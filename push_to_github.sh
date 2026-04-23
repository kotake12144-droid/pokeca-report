#!/bin/bash
set -e

cd /Users/k.k/Desktop/ebay

DATE=$(date +%Y-%m-%d)
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1496445556954763386/Dtrt2-2vWenzZL8oEWuQ-LB3g78BNnEICCLiaVRGZHQLUT1rhUwwJzpbywjhM_MMQhIs"

# GitHub push
git add docs/
git diff --staged --quiet || git commit -m "daily update: $DATE"
git push origin main
echo "✓ GitHub push"

# Vercel deploy
cd /Users/k.k/Desktop/ebay/docs
DEPLOY_URL=$(vercel --prod --yes 2>&1 | grep -o 'https://docs-[^[:space:]]*\.vercel\.app' | head -1)
if [ -n "$DEPLOY_URL" ]; then
    vercel alias set "$DEPLOY_URL" pokeca-report.vercel.app > /dev/null 2>&1
fi
echo "✓ Vercel deploy → https://pokeca-report.vercel.app/"

cd /Users/k.k/Desktop/ebay

# Discord通知
TOKEN=$(cat /Users/k.k/Desktop/ebay/docs/current_token.txt 2>/dev/null)
REPORT_URL="https://pokeca-report.vercel.app/r/${TOKEN}/"
PAYLOAD="{\"content\": \"📊 **ポケカ PSA投資レポート更新** ($DATE)\n🔗 本日のレポート: ${REPORT_URL}\n📈 推移グラフ: https://pokeca-report.vercel.app/trends.html\"}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "$DISCORD_WEBHOOK")
[ "$HTTP_STATUS" = "204" ] && echo "✓ Discord通知送信" || echo "✗ Discord通知失敗 (HTTP $HTTP_STATUS)"
