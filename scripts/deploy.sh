#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "❌ Error on line $LINENO" >&2; read -p "Press Enter to exit..."' ERR

REPO_URL="https://github.com/ilyarolf/AiogramShopBot.git"
PROJECT_DIR="AiogramShopBot"

echo "🚀 Starting deployment..."

# -------------------------
# Helpers
# -------------------------

generate_secret() {
  openssl rand -hex 16
}

validate_support_link() {
  [[ "$1" =~ ^https://[a-zA-Z0-9.-]+(/.*)?$ ]]
}

validate_currency() {
  [[ "$1" =~ ^(USD|EUR|JPY|CAD|GBP)$ ]]
}

validate_admin_ids() {
  [[ "$1" =~ ^[0-9]+(,[0-9]+)*$ ]]
}

# ---- crypto validators (1:1 with Python) ----
validate_btc() { [[ "$1" =~ ^bc1[a-zA-HJ-NP-Z0-9]{25,39}$ ]]; }
validate_ltc() { [[ "$1" =~ ^ltc1[a-zA-HJ-NP-Z0-9]{26,}$ ]]; }
validate_eth() { [[ "$1" =~ ^0x[a-fA-F0-9]{40}$ ]]; }
validate_bnb() { [[ "$1" =~ ^0x[a-fA-F0-9]{40}$ ]]; }
validate_sol() { [[ "$1" =~ ^[1-9A-HJ-NP-Za-km-z]{32,44}$ ]]; }

read_crypto_address() {
  local coin=$1
  local validator=$2
  local addr
  while true; do
    read -rp "$coin forwarding address: " addr
    if $validator "$addr"; then
      echo "$addr"
      return
    else
      echo "❌ Invalid $coin address"
    fi
  done
}

validate_telegram_token() {
  curl -sf "https://api.telegram.org/bot$1/getMe" \
    | grep -q '"is_bot":true'
}

# -------------------------
# Docker check
# -------------------------

if ! command -v docker &>/dev/null; then
  echo "🐳 Installing Docker..."
  curl -fsSL https://get.docker.com | bash
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
  echo "🐳 Installing docker-compose..."
  sudo apt install -y docker-compose
fi

# -------------------------
# Clone repo
# -------------------------

if [[ ! -d "$PROJECT_DIR" ]]; then
  git clone "$REPO_URL"
fi

cd "$PROJECT_DIR"

# -------------------------
# SERVER IP
# -------------------------


set +e
SERVER_IP=$(curl -s https://api.ipify.org)
set -e
if [[ -z "$SERVER_IP" ]]; then
  echo "❌ Could not determine SERVER_IP" >&2
  exit 1
fi
echo "🌍 Detected SERVER_IP: $SERVER_IP"

# -------------------------
# Caddyfile from template
# -------------------------

if [[ ! -f Caddyfile.template ]]; then
  echo "❌ Caddyfile.template not found" >&2
  exit 1
fi

sed "s/{SERVER_IP_ADDRESS}/${SERVER_IP}/g" \
  Caddyfile.template > Caddyfile

echo "✅ Caddyfile generated"

# -------------------------
# .env generation
# -------------------------

cp .env.template .env
sed -i 's|RUNTIME_ENVIRONMENT = "DEV"|RUNTIME_ENVIRONMENT = "PROD"|' .env

# ---- Telegram token ----
while true; do
  read -rp "Telegram BOT TOKEN: " TOKEN
  if validate_telegram_token "$TOKEN"; then
    echo "✅ Telegram token valid"
    break
  else
    echo "❌ Invalid Telegram bot token"
  fi
done
sed -i "s|TOKEN = \"\"|TOKEN = \"$TOKEN\"|" .env

# ---- Admin IDs ----
while true; do
  read -rp "ADMIN_ID_LIST (comma separated ints): " ADMIN_ID_LIST
  validate_admin_ids "$ADMIN_ID_LIST" && break
  echo "❌ Invalid ADMIN_ID_LIST"
done
sed -i "s|ADMIN_ID_LIST =|ADMIN_ID_LIST = $ADMIN_ID_LIST|" .env

# ---- Support link ----
while true; do
  read -rp "SUPPORT_LINK (https://...): " SUPPORT_LINK
  validate_support_link "$SUPPORT_LINK" && break
  echo "❌ Invalid SUPPORT_LINK"
done
sed -i "s|SUPPORT_LINK = \"\"|SUPPORT_LINK = \"$SUPPORT_LINK\"|" .env

# ---- Currency ----
while true; do
  read -rp "Currency (USD/EUR/JPY/CAD/GBP): " CURRENCY
  validate_currency "$CURRENCY" && break
  echo "❌ Invalid currency"
done
sed -i "s|CURRENCY = \"USD\"|CURRENCY = \"$CURRENCY\"|" .env

echo "🔑 KRYPTO_EXPRESS_API_KEY can be found here:"
echo "👉 https://kryptoexpress.pro/profile"
read -rp "KRYPTO_EXPRESS_API_KEY: " KRYPTO_EXPRESS_API_KEY

# ---- Secrets ----
for VAR in \
  POSTGRES_PASSWORD \
  WEBHOOK_SECRET_TOKEN \
  KRYPTO_EXPRESS_API_SECRET \
  REDIS_PASSWORD \
  SQLADMIN_RAW_PASSWORD \
  JWT_SECRET_KEY; do
  SECRET=$(generate_secret)
  sed -i "s|$VAR = \"\"|$VAR = \"$SECRET\"|" .env
done

# ---- Crypto forwarding ----
read -rp "Enable CRYPTO_FORWARDING_MODE? (true/false): " CRYPTO_MODE
sed -i "s|CRYPTO_FORWARDING_MODE = \"false\"|CRYPTO_FORWARDING_MODE = \"$CRYPTO_MODE\"|" .env

if [[ "$CRYPTO_MODE" == "true" ]]; then
  BTC_ADDR=$(read_crypto_address BTC validate_btc)
  LTC_ADDR=$(read_crypto_address LTC validate_ltc)
  ETH_ADDR=$(read_crypto_address ETH validate_eth)
  SOL_ADDR=$(read_crypto_address SOL validate_sol)
  BNB_ADDR=$(read_crypto_address BNB validate_bnb)

  sed -i "s|BTC_FORWARDING_ADDRESS = \"\"|BTC_FORWARDING_ADDRESS = \"$BTC_ADDR\"|" .env
  sed -i "s|LTC_FORWARDING_ADDRESS = \"\"|LTC_FORWARDING_ADDRESS = \"$LTC_ADDR\"|" .env
  sed -i "s|ETH_FORWARDING_ADDRESS = \"\"|ETH_FORWARDING_ADDRESS = \"$ETH_ADDR\"|" .env
  sed -i "s|SOL_FORWARDING_ADDRESS = \"\"|SOL_FORWARDING_ADDRESS = \"$SOL_ADDR\"|" .env
  sed -i "s|BNB_FORWARDING_ADDRESS = \"\"|BNB_FORWARDING_ADDRESS = \"$BNB_ADDR\"|" .env
fi

echo "✅ .env configured"

echo ""
echo "🔐 SQL Admin password:"
echo "$SQLADMIN_RAW_PASSWORD"
echo ""
echo "🌐 Admin panel is available at:"
echo "https://${SERVER_IP}.sslip.io/admin"


# -------------------------
# Run containers
# -------------------------

docker-compose up -d

echo "🎉 Deployment completed"
echo "🌐 Webhook URL: https://${SERVER_IP}.sslip.io/"
