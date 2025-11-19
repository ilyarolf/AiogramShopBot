from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db_session, session_execute, session_commit
from enums.keyboardbutton import KeyboardButton
from models.button_media import ButtonMedia, ButtonMediaDTO
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
