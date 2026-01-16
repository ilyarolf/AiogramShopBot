import json
import logging
import math
import os
import re
import urllib.request
import datetime
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext
from pyngrok import ngrok

import config
from enums.bot_entity import BotEntity
from enums.language import Language

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


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
    try:
        with open(f"./i18n/{language.value}.json", "r", encoding="UTF-8") as f:
            return json.loads(f.read())[entity.name.lower()][key]
    except Exception as e:
        logging.error(e)
        return get_text(Language.EN, entity, key)


def remove_html_tags(text: str):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def calculate_max_page(records_qty: int):
    if records_qty % config.PAGE_ENTRIES == 0:
        return records_qty / config.PAGE_ENTRIES - 1
    else:
        return math.trunc(records_qty / config.PAGE_ENTRIES)


def extract_placeholders(text: str) -> set[str]:
    PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
    placeholders = set()
    for match in PLACEHOLDER_RE.findall(text):
        name = match.split(":", 1)[0]
        placeholders.add(name)
    return placeholders


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_i18n(reference_file: str = "en.json") -> None:
    folder_path = Path("./i18n")
    reference_path = folder_path / reference_file

    if not reference_path.exists():
        raise FileNotFoundError(f"Reference file not found: {reference_path}")

    reference = load_json(reference_path)
    errors = []

    for file_path in folder_path.glob("*.json"):
        if file_path.name == reference_file:
            continue

        data = load_json(file_path)

        for section, ref_keys in reference.items():
            if section not in data:
                errors.append(
                    f"[{file_path.name}] Missing section: '{section}'"
                )
                continue

            for key, ref_value in ref_keys.items():
                if key not in data[section]:
                    errors.append(
                        f"[{file_path.name}] Missing key: '{section}.{key}'"
                    )
                    continue

                if not isinstance(ref_value, str) or not isinstance(
                        data[section][key], str
                ):
                    continue

                ref_placeholders = extract_placeholders(ref_value)
                cur_placeholders = extract_placeholders(data[section][key])

                missing = ref_placeholders - cur_placeholders
                extra = cur_placeholders - ref_placeholders

                if missing:
                    errors.append(
                        f"[{file_path.name}] "
                        f"'{section}.{key}' missing placeholders: {sorted(missing)}"
                    )

                if extra:
                    errors.append(
                        f"[{file_path.name}] "
                        f"'{section}.{key}' extra placeholders: {sorted(extra)}"
                    )

    if errors:
        print("❌ Validation errors found:\n")
        for error in errors:
            print(error)
        raise SystemExit(1)

    print("✅ All localization files are valid")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)
