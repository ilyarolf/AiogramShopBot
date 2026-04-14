import sys
from types import ModuleType, SimpleNamespace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


sys.path = [
    path for path in sys.path
    if "AiogramShopBot\\Lib" not in path and "AiogramShopBot/Lib" not in path
]


def _build_config_module() -> ModuleType:
    config = ModuleType("config")
    currency = SimpleNamespace(
        value="USD",
        get_localized_text=lambda: "USD",
        get_localized_symbol=lambda: "$",
    )
    config.PAGE_ENTRIES = 8
    config.WEBHOOK_URL = "https://example.com/"
    config.KRYPTO_EXPRESS_API_KEY = "test-api-key"
    config.KRYPTO_EXPRESS_API_URL = "https://kryptoexpress.pro/api"
    config.KRYPTO_EXPRESS_API_SECRET = "test-secret"
    config.WEBHOOK_HOST = "https://example.com"
    config.WEBAPP_HOST = "127.0.0.1"
    config.WEBAPP_PORT = 5000
    config.CRYPTO_FORWARDING_MODE = False
    config.BTC_FORWARDING_ADDRESS = "btc-forward"
    config.LTC_FORWARDING_ADDRESS = "ltc-forward"
    config.ETH_FORWARDING_ADDRESS = "eth-forward"
    config.SOL_FORWARDING_ADDRESS = "sol-forward"
    config.BNB_FORWARDING_ADDRESS = "bnb-forward"
    config.ADMIN_ID_LIST = [1]
    config.TOKEN = "token"
    config.MULTIBOT = False
    config.REDIS_HOST = "localhost"
    config.REDIS_PASSWORD = "password"
    config.CURRENCY = currency
    config.DB_USER = "postgres"
    config.DB_PASS = "postgres"
    config.DB_HOST = "localhost"
    config.DB_PORT = 5432
    config.DB_NAME = "test"
    config.JWT_EXPIRE_MINUTES = 30
    config.JWT_SECRET_KEY = "secret"
    config.JWT_ALGORITHM = "HS256"
    return config


sys.modules.setdefault("config", _build_config_module())

sqladmin_module = ModuleType("sqladmin")
sqladmin_module.ModelView = type("ModelView", (), {"__init_subclass__": classmethod(lambda cls, **kwargs: None)})
sys.modules.setdefault("sqladmin", sqladmin_module)

jose_module = ModuleType("jose")
jose_module.JWTError = Exception
jose_module.jwt = SimpleNamespace(
    encode=lambda payload, secret, algorithm=None: "token",
    decode=lambda token, secret, algorithms=None: {"sub": "test"},
)
sys.modules.setdefault("jose", jose_module)

passlib_module = ModuleType("passlib")
passlib_context_module = ModuleType("passlib.context")


class _CryptContext:
    def __init__(self, *args, **kwargs):
        pass

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return plain_password == hashed_password

    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"


passlib_context_module.CryptContext = _CryptContext
passlib_module.context = passlib_context_module
sys.modules.setdefault("passlib", passlib_module)
sys.modules.setdefault("passlib.context", passlib_context_module)

pyngrok_module = ModuleType("pyngrok")
pyngrok_module.ngrok = SimpleNamespace(
    set_auth_token=lambda token: None,
    connect=lambda *args, **kwargs: SimpleNamespace(public_url="https://example.ngrok"),
)
sys.modules.setdefault("pyngrok", pyngrok_module)

redis_module = ModuleType("redis")
redis_asyncio_module = ModuleType("redis.asyncio")


class _Redis:
    def __init__(self, *args, **kwargs):
        pass

    async def close(self):
        return None


redis_asyncio_module.Redis = _Redis
redis_module.asyncio = redis_asyncio_module
sys.modules.setdefault("redis", redis_module)
sys.modules.setdefault("redis.asyncio", redis_asyncio_module)

db_module = ModuleType("db")


async def _noop_async(*args, **kwargs):
    return None


db_module.session_execute = _noop_async
db_module.session_flush = _noop_async
db_module.session_commit = _noop_async
db_module.get_db_session = _noop_async
db_module.create_db_and_tables = _noop_async
sys.modules.setdefault("db", db_module)
