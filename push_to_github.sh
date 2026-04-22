#!/bin/bash
set -e

cd /Users/k.k/Desktop/ebay

DATE=$(date +%Y-%m-%d)

echo "Staging docs/..."
git add docs/

echo "Committing..."
git commit -m "daily update: $DATE"

echo "Pushing to origin main..."
git push origin main

echo "Push succeeded: $DATE"

if [ -n "$DISCORD_WEBHOOK" ]; then
    PAYLOAD=$(cat <<EOF
{
  "content": "📊 **ポケカ PSA投資レポート更新** ($DATE)\n🔗 最新レポート: https://kotake12144-droid.github.io/pokeca-report/\n📈 推移グラフ: https://kotake12144-droid.github.io/pokeca-report/trends.html"
}
EOF
)
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$DISCORD_WEBHOOK")
    if [ "$HTTP_STATUS" = "204" ]; then
        echo "Discord notification sent"
    else
        echo "Discord notification failed (HTTP $HTTP_STATUS)"
    fi
fi
