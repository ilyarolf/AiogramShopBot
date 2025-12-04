import secrets
import string

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import CouponManagementCallback
from enums.bot_entity import BotEntity
from enums.coupon_type import CouponType
from handlers.admin.constants import CouponsManagementStates
from enums.coupon_number_of_uses import CouponNumberOfUses
from handlers.common.common import add_pagination_buttons
from models.coupon import CouponDTO
from repositories.coupon import CouponRepository
from services.notification import NotificationService
from utils.localizator import Localizator


class CouponManagementService:
    @staticmethod
    async def get_coupon_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "create_new_coupon"),
            callback_data=CouponManagementCallback.create(
                level=1
            )
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "view_all_coupons"),
            callback_data=CouponManagementCallback.create(
                level=5
            )
        )
        kb_builder.adjust(1)
        return (Localizator.get_text(BotEntity.ADMIN, "coupons_management"),
                kb_builder)

    @staticmethod
    async def coupon_creation_get_type_of_coupon_picker(
            callback_data: CouponManagementCallback) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        for coupon_type in CouponType:
            kb_builder.button(
                text=coupon_type.get_localized(),
                callback_data=CouponManagementCallback.create(
                    level=callback_data.level + 1,
                    coupon_type=coupon_type
                )
            )
        kb_builder.adjust(1)
        kb_builder.row(callback_data.get_back_button())
        return (Localizator.get_text(BotEntity.ADMIN,
                                     "pick_type_of_coupon"),
                kb_builder)

    @staticmethod
    async def coupon_creation_get_number_of_uses_picker(
            callback_data: CouponManagementCallback) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        for coupon_number_of_use in CouponNumberOfUses:
            kb_builder.button(
                text=coupon_number_of_use.get_localized(),
                callback_data=CouponManagementCallback.create(
                    level=callback_data.level + 1,
                    coupon_type=callback_data.coupon_type,
                    number_of_uses=coupon_number_of_use
                )
            )
        kb_builder.adjust(1)
        kb_builder.row(callback_data.get_back_button())
        return (Localizator.get_text(BotEntity.ADMIN, "pick_usage_number"),
                kb_builder)

    @staticmethod
    async def request_coupon_value(callback_data: CouponManagementCallback,
                                   state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        await state.set_state(CouponsManagementStates.coupon_value)
        await state.update_data(coupon_type=callback_data.coupon_type, number_of_uses=callback_data.number_of_uses)
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "cancel"),
            callback_data=CouponManagementCallback.create(0)
        )
        return Localizator.get_text(
            BotEntity.ADMIN,
            "request_coupon_value").format(
            coupon_type=callback_data.coupon_type.get_localized(),
            number_of_uses=callback_data.number_of_uses.get_localized(),
            currency_text=config.CURRENCY.get_localized_text()
        ), kb_builder

    @staticmethod
    async def receive_coupon_value(message: Message,
                                   state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        coupon_type = CouponType(state_data['coupon_type'])
        number_of_uses = CouponNumberOfUses(state_data['number_of_uses'])
        kb_builder = InlineKeyboardBuilder()
        try:
            coupon_value = float(message.text)
            if coupon_type == CouponType.PERCENTAGE:
                assert 0 < coupon_value < 100
            await state.clear()
            await state.update_data(**state_data, coupon_value=coupon_value)
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                callback_data=CouponManagementCallback.create(
                    level=4,
                    coupon_type=coupon_type,
                    number_of_uses=number_of_uses,
                    confirmation=True
                )
            )
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                callback_data=CouponManagementCallback.create(level=0)
            )
            msg = Localizator.get_text(BotEntity.ADMIN,
                                       "create_coupon_confirmation").format(
                coupon_type=coupon_type.get_localized(),
                number_of_uses=number_of_uses.get_localized(),
                coupon_value=coupon_value,
                symbol=config.CURRENCY.get_localized_symbol() if coupon_type == CouponType.FIXED else "%"
            )
            return msg, kb_builder
        except Exception as _:
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                callback_data=CouponManagementCallback.create(0)
            )
            return Localizator.get_text(
                BotEntity.ADMIN,
                "request_coupon_value").format(
                coupon_type=coupon_type.get_localized(),
                number_of_uses=number_of_uses.get_localized(),
                currency_text=config.CURRENCY.get_localized_text()
            ), kb_builder

    @staticmethod
    async def create_coupon(callback_data: CouponManagementCallback,
                            state: FSMContext,
                            session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        safe_chars = string.ascii_uppercase.replace('I', '').replace('O', '') + \
                     string.digits.replace('0', '').replace('1', '')
        code = ''.join(secrets.choice(safe_chars) for _ in range(12))
        coupon_value = float(state_data['coupon_value'])
        coupon_dto = CouponDTO(
            code=code,
            type=callback_data.coupon_type,
            value=coupon_value,
            usage_limit=0 if callback_data.number_of_uses == CouponNumberOfUses.INFINITY else 1
        )
        coupon_dto = await CouponRepository.create(coupon_dto, session)
        await session.commit()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(callback_data.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN,
                                    "coupon_created_successfully").format(
            coupon_type=callback_data.coupon_type.get_localized(),
            number_of_uses=callback_data.number_of_uses.get_localized(),
            coupon_value=coupon_value,
            symbol=config.CURRENCY.get_localized_symbol() if callback_data.coupon_type == CouponType.FIXED else "%",
            use_before=coupon_dto.expire_datetime.strftime("%m/%d/%Y, %I:%M %p"),
            code=coupon_dto.code
        ), kb_builder

    @staticmethod
    async def view_coupons(callback_data: CouponManagementCallback,
                           session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        coupons = await CouponRepository.get_paginated(callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for coupon in coupons:
            kb_builder.button(
                text=Localizator.get_text(BotEntity.ADMIN, "coupon").format(
                    id=coupon.id
                ),
                callback_data=CouponManagementCallback.create(
                    level=callback_data.level + 1,
                    coupon_id=coupon.id
                )
            )
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder,
                                                  callback_data,
                                                  CouponRepository.get_max_page(session),
                                                  callback_data.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN,
                                    "view_all_coupons"), kb_builder

    @staticmethod
    async def view_coupon(callback_data: CouponManagementCallback,
                          session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        coupon_dto = await CouponRepository.get_by_id(callback_data.coupon_id, session)
        if callback_data.confirmation is True:
            coupon_dto.is_active = False
            await CouponRepository.update(coupon_dto, session)
            await session.commit()
        kb_builder = InlineKeyboardBuilder()
        if coupon_dto.is_active:
            kb_builder.button(
                text=Localizator.get_text(BotEntity.ADMIN, "disable"),
                callback_data=CouponManagementCallback.create(
                    level=callback_data.level,
                    coupon_id=coupon_dto.id,
                    confirmation=True
                )
            )
        kb_builder.row(callback_data.get_back_button(5))
        if coupon_dto.usage_limit == 1:
            number_of_uses = Localizator.get_text(BotEntity.ADMIN,
                                                  "single_usage")
        else:
            number_of_uses = Localizator.get_text(BotEntity.ADMIN,
                                                  "infinity_usage")
        return Localizator.get_text(BotEntity.ADMIN, "coupon_info").format(
            coupon_type=coupon_dto.type.get_localized(),
            number_of_uses=number_of_uses,
            coupon_value=coupon_dto.value,
            symbol=config.CURRENCY.get_localized_symbol() if coupon_dto.type == CouponType.FIXED else "%",
            use_before=coupon_dto.expire_datetime.strftime("%m/%d/%Y, %I:%M %p"),
            code=coupon_dto.code,
            usage_count=coupon_dto.usage_count
        ), kb_builder
