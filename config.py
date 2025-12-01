import os

from dotenv import load_dotenv

from enums.currency import Currency
from enums.runtime_environment import RuntimeEnvironment
from utils.utils import get_sslipio_external_url, start_ngrok

load_dotenv(".env")
RUNTIME_ENVIRONMENT = RuntimeEnvironment(os.environ.get("RUNTIME_ENVIRONMENT"))
if RUNTIME_ENVIRONMENT == RuntimeEnvironment.DEV:
    WEBHOOK_HOST = start_ngrok()
else:
    WEBHOOK_HOST = get_sslipio_external_url()
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH")
WEBAPP_HOST = os.environ.get("WEBAPP_HOST")
WEBAPP_PORT = int(os.environ.get("WEBAPP_PORT"))
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
TOKEN = os.environ.get("TOKEN")
ADMIN_ID_LIST = os.environ.get("ADMIN_ID_LIST").split(',')
ADMIN_ID_LIST = [int(admin_id) for admin_id in ADMIN_ID_LIST]
SUPPORT_LINK = os.environ.get("SUPPORT_LINK")
DB_ENCRYPTION = os.environ.get("DB_ENCRYPTION", False) == 'true'
DB_NAME = os.environ.get("DB_NAME")
DB_PASS = os.environ.get("DB_PASS")
PAGE_ENTRIES = int(os.environ.get("PAGE_ENTRIES"))
BOT_LANGUAGE = os.environ.get("BOT_LANGUAGE")
MULTIBOT = os.environ.get("MULTIBOT", False) == 'true'
CURRENCY = Currency(os.environ.get("CURRENCY"))
KRYPTO_EXPRESS_API_KEY = os.environ.get("KRYPTO_EXPRESS_API_KEY")
KRYPTO_EXPRESS_API_URL = os.environ.get("KRYPTO_EXPRESS_API_URL")
KRYPTO_EXPRESS_API_SECRET = os.environ.get("KRYPTO_EXPRESS_API_SECRET")
WEBHOOK_SECRET_TOKEN = os.environ.get("WEBHOOK_SECRET_TOKEN")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
CRYPTO_FORWARDING_MODE = os.environ.get("CRYPTO_FORWARDING_MODE", False) == 'true'
BTC_FORWARDING_ADDRESS = os.environ.get("BTC_FORWARDING_ADDRESS")
LTC_FORWARDING_ADDRESS = os.environ.get("LTC_FORWARDING_ADDRESS")
ETH_FORWARDING_ADDRESS = os.environ.get("ETH_FORWARDING_ADDRESS")
SOL_FORWARDING_ADDRESS = os.environ.get("SOL_FORWARDING_ADDRESS")
BNB_FORWARDING_ADDRESS = os.environ.get("BNB_FORWARDING_ADDRESS")
