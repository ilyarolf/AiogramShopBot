from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramUnauthorizedError

import config
from enums.announcement_type import AnnouncementType
from enums.language import Language
from models.user import UserDTO
from multibot import command_add_bot, on_startup
from services.announcement import AnnouncementService
from services.multibot import MultibotService
from services.notification import NotificationService


class _FakeRedis:
    def __init__(self):
        self.values = set()
        self.closed = False

    async def smembers(self, key):
        return set(self.values)

    async def sismember(self, key, value):
        return value in self.values

    async def sadd(self, key, value):
        initial_len = len(self.values)
        self.values.add(value)
        return 1 if len(self.values) != initial_len else 0

    async def srem(self, key, value):
        self.values.discard(value)
        return 1

    async def close(self):
        self.closed = True


class _FakeSession:
    async def close(self):
        return None


class _FakeBot:
    def __init__(self, token, behavior=None):
        self.token = token
        self.behavior = behavior or {}
        self.session = _FakeSession()
        self.sent_messages = []
        self.copied_messages = []
        self.webhooks = []

    async def get_me(self):
        action = self.behavior.get("get_me")
        if isinstance(action, Exception):
            raise action
        username = self.behavior.get("username", "child_bot")
        return SimpleNamespace(username=username)

    async def set_webhook(self, url, **kwargs):
        action = self.behavior.get("set_webhook")
        if isinstance(action, Exception):
            raise action
        self.webhooks.append((url, kwargs))

    async def delete_webhook(self, **kwargs):
        self.webhooks.append(("delete", kwargs))

    async def send_message(self, chat_id, text, reply_markup=None):
        action = self.behavior.get("send_message")
        if isinstance(action, Exception):
            raise action
        self.sent_messages.append((chat_id, text, reply_markup))

    async def copy_message(self, chat_id, from_chat_id, message_id):
        action = self.behavior.get("copy_message")
        if isinstance(action, Exception):
            raise action
        self.copied_messages.append((chat_id, from_chat_id, message_id))


class _FakeMessage:
    def __init__(self):
        self.answers = []
        self.chat = SimpleNamespace(id=77)
        self.message_id = 501

    async def answer(self, text):
        self.answers.append(text)
        return SimpleNamespace(message_id=900, chat=SimpleNamespace(id=123))

    async def edit_reply_markup(self):
        return None


class _FakeCallback:
    def __init__(self):
        self.message = _FakeMessage()


@pytest.mark.asyncio
async def test_multibot_token_storage_ignores_main_token():
    redis = _FakeRedis()

    assert await MultibotService.add_token("child-token", redis) is True
    assert await MultibotService.add_token("child-token", redis) is False
    assert await MultibotService.add_token(config.TOKEN, redis) is False
    assert await MultibotService.get_child_tokens(redis) == ["child-token"]

    await MultibotService.remove_token("child-token", redis)

    assert await MultibotService.get_child_tokens(redis) == []


@pytest.mark.asyncio
async def test_command_add_bot_rejects_main_token(monkeypatch):
    message = _FakeMessage()
    parent_bot = SimpleNamespace(session=_FakeSession())
    monkeypatch.setattr("multibot.is_bot_token", lambda token: True)

    await command_add_bot(message, SimpleNamespace(args=config.TOKEN), parent_bot)

    assert "main bot token" in message.answers[-1].lower()


@pytest.mark.asyncio
async def test_command_add_bot_rejects_duplicate(monkeypatch):
    message = _FakeMessage()
    parent_bot = SimpleNamespace(session=_FakeSession())
    monkeypatch.setattr("multibot.is_bot_token", lambda token: True)

    async def _fake_has_token(token):
        return True

    monkeypatch.setattr("multibot.MultibotService.has_token", _fake_has_token)

    await command_add_bot(message, SimpleNamespace(args="123:abc"), parent_bot)

    assert "already" in message.answers[-1].lower()


@pytest.mark.asyncio
async def test_command_add_bot_saves_valid_token(monkeypatch):
    message = _FakeMessage()
    parent_bot = SimpleNamespace(session=_FakeSession())
    added_tokens = []
    created_bots = []

    async def _fake_has_token(token):
        return False

    async def _fake_add_token(token):
        added_tokens.append(token)
        return True

    def _fake_bot_factory(token, session):
        bot = _FakeBot(token, behavior={"username": "shop_child"})
        bot.session = session
        created_bots.append(bot)
        return bot

    monkeypatch.setattr("multibot.is_bot_token", lambda token: True)
    monkeypatch.setattr("multibot.MultibotService.has_token", _fake_has_token)
    monkeypatch.setattr("multibot.MultibotService.add_token", _fake_add_token)
    monkeypatch.setattr("multibot.Bot", _fake_bot_factory)

    await command_add_bot(message, SimpleNamespace(args="123456:ABCDEF"), parent_bot)

    assert added_tokens == ["123456:ABCDEF"]
    assert "shop_child" in message.answers[-1]
    assert created_bots[0].webhooks[-1][0].endswith("/webhook/bot/123456:ABCDEF")


@pytest.mark.asyncio
async def test_restore_child_bot_webhooks_removes_unauthorized_token(monkeypatch):
    created_bots = {}
    removed_tokens = []

    async def _fake_get_child_tokens(redis_client=None):
        return ["good-token", "bad-token"]

    async def _fake_remove_token(token, redis_client=None):
        removed_tokens.append(token)

    def _fake_build_bot(token):
        behavior = {"username": "restored"}
        if token == "bad-token":
            behavior["get_me"] = TelegramUnauthorizedError(
                method=SimpleNamespace(__api_method__="getMe"),
                message="unauthorized"
            )
        bot = _FakeBot(token, behavior=behavior)
        created_bots[token] = bot
        return bot

    monkeypatch.setattr("services.multibot.MultibotService.get_child_tokens", _fake_get_child_tokens)
    monkeypatch.setattr("services.multibot.MultibotService.remove_token", _fake_remove_token)
    monkeypatch.setattr("services.multibot.MultibotService.build_bot", _fake_build_bot)

    await MultibotService.restore_child_bot_webhooks("https://example.com/webhook/bot/{bot_token}")

    assert created_bots["good-token"].webhooks[-1][0].endswith("/good-token")
    assert removed_tokens == ["bad-token"]


@pytest.mark.asyncio
async def test_send_to_user_multibot_uses_all_tokens_and_sleep(monkeypatch):
    sleep_calls = []
    built_bots = []

    async def _fake_get_all_tokens(redis_client=None):
        return ["main-token", "child-token"]

    async def _fake_sleep(delay):
        sleep_calls.append(delay)

    def _fake_build_bot(token):
        bot = _FakeBot(token)
        built_bots.append(bot)
        return bot

    monkeypatch.setattr("services.multibot.MultibotService.get_all_tokens_with_main", _fake_get_all_tokens)
    monkeypatch.setattr("services.multibot.MultibotService.build_bot", _fake_build_bot)
    monkeypatch.setattr("services.multibot.asyncio.sleep", _fake_sleep)

    sent_count = await MultibotService.send_message_to_user("hello", 100500)

    assert sent_count == 2
    assert [bot.token for bot in built_bots] == ["main-token", "child-token"]
    assert sleep_calls == [0.3]


@pytest.mark.asyncio
async def test_notification_service_send_to_user_uses_multibot_service(monkeypatch):
    called = []
    monkeypatch.setattr("config.MULTIBOT", True)

    async def _fake_send_message_to_user(message, telegram_id, reply_markup=None):
        called.append((message, telegram_id, reply_markup))
        return 2

    monkeypatch.setattr("services.notification.MultibotService.send_message_to_user", _fake_send_message_to_user)

    await NotificationService.send_to_user("hello", 42)

    assert called == [("hello", 42, None)]


@pytest.mark.asyncio
async def test_announcement_service_counts_multibot_successes(monkeypatch):
    callback = _FakeCallback()
    updates = []
    user = UserDTO(telegram_id=777, can_receive_messages=True)

    monkeypatch.setattr("config.MULTIBOT", True)
    
    async def _fake_get_active(session):
        return [user]

    async def _fake_get_all_count(session):
        return 1

    async def _fake_copy_message(from_chat_id, message_id, telegram_id):
        return 2, False

    async def _fake_edit_message(message, source_message_id, chat_id):
        updates.append(message)

    async def _fake_session_commit(session):
        return None

    monkeypatch.setattr("services.announcement.UserRepository.get_active", _fake_get_active)
    monkeypatch.setattr("services.announcement.UserRepository.get_all_count", _fake_get_all_count)
    monkeypatch.setattr("services.announcement.MultibotService.copy_message_to_user", _fake_copy_message)
    monkeypatch.setattr("services.announcement.NotificationService.edit_message", _fake_edit_message)
    monkeypatch.setattr("services.announcement.session_commit", _fake_session_commit)

    await AnnouncementService.send_announcement(
        callback,
        SimpleNamespace(announcement_type=AnnouncementType.CURRENT_STOCK),
        object(),
        Language.EN
    )

    assert any("2" in message for message in updates)


@pytest.mark.asyncio
async def test_announcement_service_marks_user_inactive_when_all_multibot_attempts_forbidden(monkeypatch):
    callback = _FakeCallback()
    updated_users = []
    user = UserDTO(telegram_id=777, can_receive_messages=True)

    monkeypatch.setattr("config.MULTIBOT", True)
    
    async def _fake_get_active(session):
        return [user]

    async def _fake_get_all_count(session):
        return 1

    async def _fake_copy_message(from_chat_id, message_id, telegram_id):
        return 0, True

    async def _fake_update(user_dto, session):
        updated_users.append(user_dto)

    async def _fake_edit_message(message, source_message_id, chat_id):
        return None

    async def _fake_session_commit(session):
        return None

    monkeypatch.setattr("services.announcement.UserRepository.get_active", _fake_get_active)
    monkeypatch.setattr("services.announcement.UserRepository.get_all_count", _fake_get_all_count)
    monkeypatch.setattr("services.announcement.MultibotService.copy_message_to_user", _fake_copy_message)
    monkeypatch.setattr("services.announcement.UserRepository.update", _fake_update)
    monkeypatch.setattr("services.announcement.NotificationService.edit_message", _fake_edit_message)
    monkeypatch.setattr("services.announcement.session_commit", _fake_session_commit)

    await AnnouncementService.send_announcement(
        callback,
        SimpleNamespace(announcement_type=AnnouncementType.CURRENT_STOCK),
        object(),
        Language.EN
    )

    assert updated_users
    assert updated_users[0].can_receive_messages is False


@pytest.mark.asyncio
async def test_multibot_startup_restores_child_webhooks(monkeypatch):
    restored = []
    created = []

    async def _fake_create_db_and_tables():
        created.append(True)

    async def _fake_restore(url):
        restored.append(url)

    bot = _FakeBot("main-token")

    monkeypatch.setattr("multibot.create_db_and_tables", _fake_create_db_and_tables)
    monkeypatch.setattr("multibot.MultibotService.restore_child_bot_webhooks", _fake_restore)

    await on_startup(SimpleNamespace(), bot)

    assert created == [True]
    assert restored == ["https://example.com/webhook/bot/{bot_token}"]
