from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from db import session_flush, session_execute
from models.review import ReviewDTO, Review
from utils.utils import calculate_max_page


class ReviewRepository:
    @staticmethod
    async def create(review_dto: ReviewDTO, session: AsyncSession) -> ReviewDTO:
        coupon = Review(**review_dto.model_dump())
        session.add(coupon)
        await session_flush(session)
        return ReviewDTO.model_validate(coupon, from_attributes=True)

    @staticmethod
    async def get_by_buy_item_id(buyItem_id: int, session: AsyncSession) -> ReviewDTO | None:
        stmt = select(Review).where(Review.buyItem_id == buyItem_id)
        review_dto = await session_execute(stmt, session)
        review_dto = review_dto.scalar_one_or_none()
        if review_dto is not None:
            review_dto = ReviewDTO.model_validate(review_dto, from_attributes=True)
        return review_dto

    @staticmethod
    async def get_reviews_paginated(page: int, session: AsyncSession) -> list[ReviewDTO]:
        stmt = (select(Review)
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(Review.create_datetime.desc()))
        reviews = await session_execute(stmt, session)
        return [ReviewDTO.model_validate(review, from_attributes=True) for review in reviews.scalars().all()]

    @staticmethod
    async def get_max_page(session: AsyncSession) -> int:
        sub_stmt = (select(Review))
        stmt = select(func.count()).select_from(sub_stmt)
        max_page = await session_execute(stmt, session)
        return calculate_max_page(max_page.scalar_one())

    @staticmethod
    async def get_by_id(review_id: int, session: AsyncSession) -> ReviewDTO:
        stmt = select(Review).where(Review.id == review_id)
        review = await session_execute(stmt, session)
        return ReviewDTO.model_validate(review.scalar_one(), from_attributes=True)

    @staticmethod
    async def update(review_dto: ReviewDTO, session: AsyncSession):
        stmt = update(Review).where(Review.id == review_dto.id).values(**review_dto.model_dump())
        await session_execute(stmt, session)
