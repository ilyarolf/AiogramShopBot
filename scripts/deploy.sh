#!/bin/sh
set -eu

REPO_URL="https://github.com/ilyarolf/AiogramShopBot.git"
PROJECT_DIR="AiogramShopBot"

echo "🚀 Starting deployment..."

# -------------------------
# Helpers
# -------------------------

generate_secret() {
  openssl rand -hex 16
}

validate_currency() {
  case "$1" in
    USD|EUR|JPY|CAD|GBP) return 0 ;;
    *) return 1 ;;
  esac
}

validate_admin_ids() {
  echo "$1" | grep -Eq '^[0-9]+(,[0-9]+)*$'
}

validate_support_link() {
  echo "$1" | grep -Eq '^https://'
}

validate_btc() { echo "$1" | grep -Eq '^bc1[a-zA-HJ-NP-Z0-9]{25,39}$'; }
validate_ltc() { echo "$1" | grep -Eq '^ltc1[a-zA-HJ-NP-Z0-9]{26,}$'; }
validate_eth() { echo "$1" | grep -Eq '^0x[a-fA-F0-9]{40}$'; }
validate_bnb() { echo "$1" | grep -Eq '^0x[a-fA-F0-9]{40}$'; }
validate_sol() { echo "$1" | grep -Eq '^[1-9A-HJ-NP-Za-km-z]{32,44}$'; }

read_crypto_address() {
  COIN="$1"
  VALIDATOR="$2"

  while :; do
    printf "%s forwarding address: " "$COIN" >&2
    read ADDR
    if "$VALIDATOR" "$ADDR"; then
      echo "$ADDR"
      return
    fi
    echo "❌ Invalid $COIN address" >&2
  done
}

validate_telegram_token() {
  curl -fs "https://api.telegram.org/bot$1/getMe"
}

# -------------------------
# Docker install/check
# -------------------------

if ! command -v docker >/dev/null 2>&1; then
  echo "🐳 Docker not found, installing..."
  curl -fsSL https://get.docker.com | sh
fi

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker-compose"
else
  echo "❌ docker-compose not found"
  exit 1
fi

echo "🐳 Docker is ready"

# -------------------------
# Clone repository
# -------------------------

if [ ! -d "$PROJECT_DIR" ]; then
  git clone "$REPO_URL"
fi

cd "$PROJECT_DIR"

# -------------------------
# Detect SERVER IP
# -------------------------

echo "🌍 Detecting server IP..."
SERVER_IP=$(curl -fs https://api.ipify.org)

if [ -z "$SERVER_IP" ]; then
  echo "❌ Could not determine SERVER_IP"
  exit 1
fi

echo "🌍 Server IP: $SERVER_IP"

# -------------------------
# Generate Caddyfile
# -------------------------

sed "s/{SERVER_IP_ADDRESS}/${SERVER_IP}/g" \
  Caddyfile.template > Caddyfile

echo "✅ Caddyfile generated"

# -------------------------
# Telegram bot validation
# -------------------------

while :; do
  printf "Telegram BOT TOKEN: "
  read TOKEN

  BOT_INFO=$(validate_telegram_token "$TOKEN" || true)

  echo "$BOT_INFO" | grep -q '"is_bot":true' && break
  echo "❌ Invalid Telegram bot token"
done

BOT_USERNAME=$(echo "$BOT_INFO" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')

if [ -n "$BOT_USERNAME" ]; then
  echo "🤖 Bot username: @$BOT_USERNAME"
else
  echo "⚠️ Bot username not found"
fi

# -------------------------
# User input
# -------------------------

while :; do
  printf "ADMIN_ID_LIST (comma separated ints): "
  read ADMIN_ID_LIST
  validate_admin_ids "$ADMIN_ID_LIST" && break
  echo "❌ Invalid ADMIN_ID_LIST"
done

while :; do
  printf "SUPPORT_LINK (https://...): "
  read SUPPORT_LINK
  validate_support_link "$SUPPORT_LINK" && break
  echo "❌ SUPPORT_LINK must start with https://"
done

while :; do
  printf "Currency (USD/EUR/JPY/CAD/GBP): "
  read CURRENCY
  validate_currency "$CURRENCY" && break
  echo "❌ Invalid currency"
done

echo "🔑 KRYPTO_EXPRESS_API_KEY can be obtained here:"
echo "👉 https://kryptoexpress.pro/profile"
printf "KRYPTO_EXPRESS_API_KEY: "
read KRYPTO_EXPRESS_API_KEY

printf "Enable CRYPTO_FORWARDING_MODE? (true/false): "
read CRYPTO_MODE

if [ "$CRYPTO_MODE" = "true" ]; then
  BTC_ADDR=$(read_crypto_address BTC validate_btc)
  LTC_ADDR=$(read_crypto_address LTC validate_ltc)
  ETH_ADDR=$(read_crypto_address ETH validate_eth)
  SOL_ADDR=$(read_crypto_address SOL validate_sol)
  BNB_ADDR=$(read_crypto_address BNB validate_bnb)
else
  BTC_ADDR=""
  LTC_ADDR=""
  ETH_ADDR=""
  SOL_ADDR=""
  BNB_ADDR=""
fi

# -------------------------
# Generate secrets
# -------------------------

POSTGRES_PASSWORD=$(generate_secret)
WEBHOOK_SECRET_TOKEN=$(generate_secret)
KRYPTO_EXPRESS_API_SECRET=$(generate_secret)
REDIS_PASSWORD=$(generate_secret)
SQLADMIN_RAW_PASSWORD=$(generate_secret)
JWT_SECRET_KEY=$(generate_secret)

# -------------------------
# Write .env
# -------------------------

cat > .env <<EOF
WEBHOOK_PATH="/"
WEBAPP_HOST="0.0.0.0"
WEBAPP_PORT="5000"
TOKEN="$TOKEN"
ADMIN_ID_LIST=$ADMIN_ID_LIST
SUPPORT_LINK="$SUPPORT_LINK"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
DB_PORT="5432"
DB_HOST="postgres"
POSTGRES_DB="aiogram-shop-bot"
PAGE_ENTRIES="8"
MULTIBOT="false"
CURRENCY="$CURRENCY"
RUNTIME_ENVIRONMENT="PROD"
WEBHOOK_SECRET_TOKEN="$WEBHOOK_SECRET_TOKEN"
KRYPTO_EXPRESS_API_KEY="$KRYPTO_EXPRESS_API_KEY"
KRYPTO_EXPRESS_API_URL="https://kryptoexpress.pro/api"
KRYPTO_EXPRESS_API_SECRET="$KRYPTO_EXPRESS_API_SECRET"
REDIS_PASSWORD="$REDIS_PASSWORD"
REDIS_HOST="redis"
CRYPTO_FORWARDING_MODE="$CRYPTO_MODE"
BTC_FORWARDING_ADDRESS="$BTC_ADDR"
LTC_FORWARDING_ADDRESS="$LTC_ADDR"
ETH_FORWARDING_ADDRESS="$ETH_ADDR"
SOL_FORWARDING_ADDRESS="$SOL_ADDR"
BNB_FORWARDING_ADDRESS="$BNB_ADDR"
SQLADMIN_RAW_PASSWORD="$SQLADMIN_RAW_PASSWORD"
JWT_EXPIRE_MINUTES="30"
JWT_ALGORITHM="HS256"
JWT_SECRET_KEY="$JWT_SECRET_KEY"
EOF

echo "✅ .env generated"

# -------------------------
# Start containers
# -------------------------

echo "🐳 Starting Docker containers..."
$DOCKER_COMPOSE up -d

# -------------------------
# Output info
# -------------------------

echo ""
echo "🔐 SQL Admin password:"
echo "$SQLADMIN_RAW_PASSWORD"
echo ""
echo "🌐 Admin panel is available at:"
echo "https://${SERVER_IP}.sslip.io/admin"
echo ""
echo "🎉 Deployment completed successfully"
