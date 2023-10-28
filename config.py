from dotenv import load_dotenv
import os

load_dotenv()

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH")
WEBAPP_HOST = os.environ.get("WEBAPP_HOST")
WEBAPP_PORT = os.environ.get("WEBAPP_PORT")
DB_PASS = os.environ.get("DB_PASS")
MNEMONIC = os.environ.get("MNEMONIC")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
TOKEN = os.environ.get("TOKEN")
ADMIN_ID_LIST = os.environ.get("ADMIN_ID_LIST").split(',')
ADMIN_ID_LIST = [int(admin_id) for admin_id in ADMIN_ID_LIST]
SUPPORT_LINK = os.environ.get("SUPPORT_LINK")
DB_NAME = os.environ.get("DB_NAME")
DB_ENCRYPTION = os.environ.get("DB_ENCRYPTION") == "True"
ADDITIVE = os.environ.get("ADDITIVE")
