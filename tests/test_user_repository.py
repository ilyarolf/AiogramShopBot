import pytest

from enums.language import Language
from models.user import UserDTO
from repositories.user import UserRepository


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _UserOrm:
    id = 7
    telegram_username = "tester"
    telegram_id = 123456
    top_up_amount = 0.0
    consume_records = 0.0
    registered_at = None
    can_receive_messages = True
    language = Language.EN
    is_banned = False
    referral_code = "REF123"
    referred_by_user_id = None
    referred_at = None


@pytest.mark.asyncio
async def test_get_by_referrer_code_returns_dto(monkeypatch):
    async def fake_session_execute(stmt, session):
        return _ScalarResult(_UserOrm())

    monkeypatch.setattr("repositories.user.session_execute", fake_session_execute)

    user = await UserRepository.get_by_referrer_code("REF123", session=None)

    assert isinstance(user, UserDTO)
    assert user.referral_code == "REF123"
