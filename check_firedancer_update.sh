#!/bin/bash
# Firedancer update checker with Telegram notifications - v2
# Fixed: HTML formatting, API response check, no upgrade commands in message

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN="8593224607:AAF1C7xtAr29Y8FFt-sNMrvGdN6Sn-N8T04"
TELEGRAM_CHAT_ID="527058142"
LAST_VERSION_FILE="/root/.last_firedancer_version"
REPO="firedancer-io/firedancer"
# ====================

get_latest_tag() {
    curl -s "https://api.github.com/repos/$REPO/releases" | \
    jq -r '.[0].tag_name // empty' | grep -v prealpha
}

get_latest_patch() {
    get_latest_tag | grep -oP '\d+$'
}

get_current_patch() {
    /usr/local/bin/fdctl version 2>/dev/null | grep -oP '\d{5,}' | head -1 || echo "0"
}

send_telegram() {
    local message="$1"
    local response
    response=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d "chat_id=$TELEGRAM_CHAT_ID" \
        --data-urlencode "text=$message" \
        -d "parse_mode=HTML")
    
    if echo "$response" | grep -q '"ok":true'; then
        echo "Telegram notification sent successfully"
        return 0
    else
        echo "Telegram notification FAILED:"
        echo "$response"
        return 1
    fi
}

LATEST_TAG=$(get_latest_tag)
LATEST_PATCH=$(get_latest_patch)
CURRENT_PATCH=$(get_current_patch)
echo "$(date): Current patch: $CURRENT_PATCH, Latest tag: $LATEST_TAG (patch: $LATEST_PATCH)"

if [ -z "$LATEST_PATCH" ] || [ -z "$CURRENT_PATCH" ]; then
    echo "Failed to parse version numbers, skipping"
    exit 1
fi

if [ "$LATEST_PATCH" -gt "$CURRENT_PATCH" ]; then
    if [ ! -f "$LAST_VERSION_FILE" ] || [ "$(cat $LAST_VERSION_FILE)" != "$LATEST_TAG" ]; then

        MESSAGE="🚀 <b>Firedancer Update Available</b>

Current patch: <code>$CURRENT_PATCH</code>
Latest: <code>$LATEST_TAG</code>

<a href=\"https://github.com/firedancer-io/firedancer/releases/tag/$LATEST_TAG\">Release notes</a>

⚠️ Use your tested upgrade runbook. Do not paste commands from chat directly."

        if send_telegram "$MESSAGE"; then
            echo "$LATEST_TAG" > "$LAST_VERSION_FILE"
        else
            echo "State file NOT updated - will retry on next run"
        fi
    fi
fi
