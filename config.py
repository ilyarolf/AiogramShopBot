from dotenv import load_dotenv
import os

from ngrok_executor import start_ngrok

load_dotenv()

WEBHOOK_HOST = start_ngrok()
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH")
WEBAPP_HOST = os.environ.get("WEBAPP_HOST")
WEBAPP_PORT = os.environ.get("WEBAPP_PORT")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
TOKEN = os.environ.get("TOKEN")
ADMIN_ID_LIST = os.environ.get("ADMIN_ID_LIST").split(',')
ADMIN_ID_LIST = [int(admin_id) for admin_id in ADMIN_ID_LIST]
SUPPORT_LINK = os.environ.get("SUPPORT_LINK")
DB_NAME = os.environ.get("DB_NAME")
PAGE_ENTRIES = int(os.environ.get("PAGE_ENTRIES"))
