from types import SimpleNamespace

import pytest

from callbacks import AnnouncementCallback
from enums.announcement_type import AnnouncementType
from enums.language import Language
from handlers.admin.announcement import send_generated_msg


class _FakeMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))
        return SimpleNamespace()


class _FakeCallback:
    def __init__(self):
        self.message = _FakeMessage()


@pytest.mark.asyncio
async def test_send_generated_msg_sends_first_chunk_with_keyboard_only(monkeypatch):
    callback = _FakeCallback()

    async def _fake_create_announcement_message(*args, **kwargs):
        return ["chunk-1", "chunk-2", "chunk-3"]

    monkeypatch.setattr(
        "handlers.admin.announcement.ItemService.create_announcement_message",
        _fake_create_announcement_message
    )

    await send_generated_msg(
        callback=callback,
        session=None,
        callback_data=AnnouncementCallback.create(2, AnnouncementType.CURRENT_STOCK),
        language=Language.EN
    )

    assert [answer[0] for answer in callback.message.answers] == ["chunk-1", "chunk-2", "chunk-3"]
    assert callback.message.answers[0][1] is not None
    assert callback.message.answers[1][1] is None
    assert callback.message.answers[2][1] is None
