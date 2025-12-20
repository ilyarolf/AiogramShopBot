import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import config
from db import session_execute
from models.shipping_option import ShippingOptionDTO, ShippingOption


class ShippingOptionRepository:
    @staticmethod
    async def create_single(shipping_option_dto: ShippingOptionDTO, session: AsyncSession):
        shipping_option = ShippingOption(**shipping_option_dto.model_dump())
        session.add(shipping_option)

    @staticmethod
    async def get_paginated(page: int,
                            is_disabled: bool | None,
                            session: AsyncSession) -> list[ShippingOptionDTO]:
        conditions = []
        if is_disabled:
            conditions.append(ShippingOption.is_disabled == is_disabled)
        stmt = (select(ShippingOption)
                .where(*conditions)
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(ShippingOption.name))
        shipping_options = await session_execute(stmt, session)
        return [ShippingOptionDTO
                .model_validate(shipping_option,
                                from_attributes=True) for shipping_option in shipping_options.scalars().all()]

    @staticmethod
    async def get_max_page(is_disabled: bool | None, session: AsyncSession) -> int:
        conditions = []
        if is_disabled:
            conditions.append(ShippingOption.is_disabled == is_disabled)
        sub_stmt = select(ShippingOption).where(*conditions)
        stmt = select(func.count()).select_from(sub_stmt)
        max_page = await session_execute(stmt, session)
        max_page = max_page.scalar_one()
        if max_page % config.PAGE_ENTRIES == 0:
            return max_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(shipping_option_id: int, session: AsyncSession) -> ShippingOptionDTO:
        stmt = select(ShippingOption).where(ShippingOption.id == shipping_option_id)
        shipping_option = await session_execute(stmt, session)
        return ShippingOptionDTO.model_validate(shipping_option.scalar_one(), from_attributes=True)
