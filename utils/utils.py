import json
import os
import urllib.request
from pyngrok import ngrok
from enums.bot_entity import BotEntity
from enums.language import Language


def get_sslipio_external_url():
    external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    sslip_url = "https://" + external_ip + ".sslip.io"
    print("external URL: " + sslip_url)
    return sslip_url


def get_bot_photo_id() -> str:
    with open("static/no_image.jpeg", "r") as f:
        return f.read()


def start_ngrok():
    ngrok_token = os.environ.get("NGROK_TOKEN")
    port = os.environ.get("WEBAPP_PORT")
    ngrok.set_auth_token(ngrok_token)
    http_tunnel = ngrok.connect(f":{port}", "http")
    return http_tunnel.public_url


def get_text(language: Language, entity: BotEntity, key: str) -> str:
    with open(f"./i18n/{language.value}.json", "r", encoding="UTF-8") as f:
        return json.loads(f.read())[entity.name.lower()][key]
