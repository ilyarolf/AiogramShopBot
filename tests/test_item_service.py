from types import SimpleNamespace

import pytest

from enums.announcement_type import AnnouncementType
from enums.language import Language
from services.item import ItemService


def _build_item(category_id: int, subcategory_id: int, price: float = 10.0):
    return SimpleNamespace(category_id=category_id, subcategory_id=subcategory_id, price=price)


@pytest.mark.asyncio
async def test_create_announcement_message_returns_single_chunk_for_short_content(monkeypatch):
    async def _fake_get_items(session):
        return [
            _build_item(1, 10),
            _build_item(1, 11),
        ]

    async def _fake_get_categories(ids, session):
        return [SimpleNamespace(id=1, name="Category 1")]

    async def _fake_get_subcategories(ids, session):
        return [
            SimpleNamespace(id=10, name="Sub 1"),
            SimpleNamespace(id=11, name="Sub 2"),
        ]

    monkeypatch.setattr("services.item.ItemRepository.get_in_stock", _fake_get_items)
    monkeypatch.setattr("services.item.CategoryRepository.get_by_ids", _fake_get_categories)
    monkeypatch.setattr("services.item.SubcategoryRepository.get_by_ids", _fake_get_subcategories)

    messages = await ItemService.create_announcement_message(
        AnnouncementType.CURRENT_STOCK,
        session=None,
        language=Language.EN
    )

    assert len(messages) == 1
    assert messages[0].startswith("<b>")
    assert "Category 1" in messages[0]


@pytest.mark.asyncio
async def test_create_announcement_message_splits_long_content_by_category(monkeypatch):
    async def _fake_get_items(session):
        return [_build_item(category_id=index, subcategory_id=index) for index in range(1, 60)]

    async def _fake_get_categories(ids, session):
        return [SimpleNamespace(id=index, name=f"Category {index} {'X' * 80}") for index in ids]

    async def _fake_get_subcategories(ids, session):
        return [SimpleNamespace(id=index, name=f"Subcategory {index} {'Y' * 60}") for index in ids]

    monkeypatch.setattr("services.item.ItemRepository.get_in_stock", _fake_get_items)
    monkeypatch.setattr("services.item.CategoryRepository.get_by_ids", _fake_get_categories)
    monkeypatch.setattr("services.item.SubcategoryRepository.get_by_ids", _fake_get_subcategories)

    messages = await ItemService.create_announcement_message(
        AnnouncementType.CURRENT_STOCK,
        session=None,
        language=Language.EN
    )

    assert len(messages) > 1
    assert all(len(message) < ItemService.ANNOUNCEMENT_MESSAGE_LIMIT for message in messages)
    assert "Category 1" in messages[0]


@pytest.mark.asyncio
async def test_create_announcement_message_splits_large_single_category_without_losing_header(monkeypatch):
    async def _fake_get_items(session):
        return [_build_item(category_id=1, subcategory_id=index) for index in range(1, 80)]

    async def _fake_get_categories(ids, session):
        return [SimpleNamespace(id=1, name="Single Category")]

    async def _fake_get_subcategories(ids, session):
        return [SimpleNamespace(id=index, name=f"Subcategory {index} {'Z' * 70}") for index in ids]

    monkeypatch.setattr("services.item.ItemRepository.get_new", _fake_get_items)
    monkeypatch.setattr("services.item.CategoryRepository.get_by_ids", _fake_get_categories)
    monkeypatch.setattr("services.item.SubcategoryRepository.get_by_ids", _fake_get_subcategories)

    messages = await ItemService.create_announcement_message(
        AnnouncementType.RESTOCKING,
        session=None,
        language=Language.EN
    )

    assert len(messages) > 1
    assert all("Single Category" in message for message in messages)
    assert all(len(message) < ItemService.ANNOUNCEMENT_MESSAGE_LIMIT for message in messages)
