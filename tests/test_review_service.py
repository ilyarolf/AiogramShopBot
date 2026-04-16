from types import SimpleNamespace

import pytest

from callbacks import ReviewManagementCallback
from enums.language import Language
from services.review import ReviewService


class _State:
    def __init__(self, data):
        self._data = data
        self.cleared = False

    async def get_data(self):
        return dict(self._data)

    async def clear(self):
        self.cleared = True


class _Session:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_review_confirmation_uses_subcategory_id(monkeypatch):
    callback_data = ReviewManagementCallback.create(level=4, buy_id=1, buyItem_id=2, rating=5)
    requested_subcategory_ids = []

    async def _fake_get_buy_item(*args, **kwargs):
        return SimpleNamespace(item_ids=[9])

    async def _fake_get_item(*args, **kwargs):
        return SimpleNamespace(category_id=11, subcategory_id=77, price=15.0, item_type=SimpleNamespace(
            get_localized=lambda language: "Digital"
        ))

    async def _fake_get_category(*args, **kwargs):
        return SimpleNamespace(name="Category")

    async def _fake_get_subcategory(subcategory_id, *args, **kwargs):
        requested_subcategory_ids.append(subcategory_id)
        return SimpleNamespace(name="Subcategory")

    monkeypatch.setattr("services.review.BuyItemRepository.get_by_id", _fake_get_buy_item)
    monkeypatch.setattr("services.review.ItemRepository.get_by_id", _fake_get_item)
    monkeypatch.setattr("services.review.CategoryRepository.get_by_id", _fake_get_category)
    monkeypatch.setattr("services.review.SubcategoryRepository.get_by_id", _fake_get_subcategory)
    monkeypatch.setattr("services.review.get_bot_photo_id", lambda: "bot-photo-id")

    await ReviewService.review_confirmation(callback_data, _State({"review_text": "ok"}), session=None, language=Language.EN)

    assert requested_subcategory_ids == [77]


@pytest.mark.asyncio
async def test_create_review_checks_duplicate_by_buy_item_id(monkeypatch):
    callback_data = ReviewManagementCallback.create(level=4, buy_id=1, buyItem_id=22, review_id=999, rating=5)
    requested_ids = []

    async def _fake_get_by_buy_item_id(buy_item_id, *args, **kwargs):
        requested_ids.append(buy_item_id)
        return SimpleNamespace(id=1, buyItem_id=buy_item_id)

    async def _fake_new_review_published(*args, **kwargs):
        return None

    monkeypatch.setattr("services.review.ReviewRepository.get_by_buy_item_id", _fake_get_by_buy_item_id)
    monkeypatch.setattr("services.review.NotificationService.new_review_published", _fake_new_review_published)
    monkeypatch.setattr("services.review.get_bot_photo_id", lambda: "bot-photo-id")

    media, _ = await ReviewService.create_review(
        callback_data,
        _State({"review_text": "ok"}),
        session=_Session(),
        language=Language.EN
    )

    assert requested_ids == [22]
    assert media.caption
