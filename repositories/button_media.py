from sqlalchemy import select, update, distinct, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db_session, session_execute, session_commit
from enums.keyboard_button import KeyboardButton
from models.button_media import ButtonMedia, ButtonMediaDTO
from models.category import Category
from models.review import Review
from models.subcategory import Subcategory
from utils.utils import get_bot_photo_id


class ButtonMediaRepository:

    @staticmethod
    async def init_buttons_media():
        bot_media_id = get_bot_photo_id()
        async with get_db_session() as session:
            for button in KeyboardButton:
                exists_stmt = select(ButtonMedia).where(ButtonMedia.button == button)
                is_exists = await session_execute(exists_stmt, session)
                is_exists = is_exists.scalar_one_or_none()
                if is_exists is None:
                    button_obj = ButtonMedia(media_id=f"0{bot_media_id}", button=button)
                    session.add(button_obj)
            await session_commit(session)

    @staticmethod
    async def get_by_button(button: KeyboardButton, session: AsyncSession) -> ButtonMediaDTO:
        stmt = (select(ButtonMedia)
                .where(ButtonMedia.button == button))
        button_media = await session_execute(stmt, session)
        return ButtonMediaDTO.model_validate(button_media.scalar_one(), from_attributes=True)

    @staticmethod
    async def update(button_media_dto: ButtonMediaDTO, session: AsyncSession):
        stmt = (update(ButtonMedia)
                .where(ButtonMedia.button == button_media_dto.button)
                .values(**button_media_dto.model_dump()))
        await session_execute(stmt, session)

    @staticmethod
    async def get_all_file_ids(session: AsyncSession) -> list[str]:
        stmt = select(
            distinct(
                union_all(
                    select(Category.media_id).where(Category.media_id != None),
                    select(Subcategory.media_id).where(Subcategory.media_id != None),
                    select(ButtonMedia.media_id).where(ButtonMedia.media_id != None),
                    select(Review.image_id).where(Review.image_id != None),
                ).subquery().c[0]
            )
        )
        result = await session_execute(stmt, session)
        return result.scalars().all()

    @staticmethod
    async def update_media_id(old_media_id: str, new_media_id: str, session: AsyncSession):
        stmt_category = (
            update(Category)
            .where(Category.media_id == old_media_id)
            .values(media_id=new_media_id)
        )

        stmt_subcategory = (
            update(Subcategory)
            .where(Subcategory.media_id == old_media_id)
            .values(media_id=new_media_id)
        )

        stmt_buttonmedia = (
            update(ButtonMedia)
            .where(ButtonMedia.media_id == old_media_id)
            .values(media_id=new_media_id)
        )

        stmt_review = (
            update(Review)
            .where(Review.image_id == old_media_id)
            .values(image_id=new_media_id)
        )
        await session_execute(stmt_category, session)
        await session_execute(stmt_subcategory, session)
        await session_execute(stmt_buttonmedia, session)
        await session_execute(stmt_review, session)

