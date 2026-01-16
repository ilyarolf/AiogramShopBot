from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import AdminMenuCallback, ShippingManagementCallback
from enums.bot_entity import BotEntity
from enums.language import Language
from enums.shipping_management_action import ShippingManagementAction
from enums.shipping_type_property import ShippingOptionProperty
from handlers.admin.constants import ShippingManagementStates
from handlers.common.common import add_pagination_buttons
from models.shipping_option import ShippingOptionDTO
from repositories.shipping_option import ShippingOptionRepository
from services.notification import NotificationService
from utils.utils import get_text


class ShippingManagementService:
    @staticmethod
    async def get_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "create_new_shipping_option",
                          ),
            callback_data=ShippingManagementCallback.create(1)
        )
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "view_all_shipping_options",
                          ),
            callback_data=ShippingManagementCallback.create(2)
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button",
                          ),
            callback_data=AdminMenuCallback.create(0)
        )
        kb_builder.adjust(1)
        return (get_text(language, BotEntity.ADMIN, "shipping_management"),
                kb_builder)

    @staticmethod
    async def create_shipping_option(callback: CallbackQuery,
                                     state: FSMContext,
                                     session: AsyncSession,
                                     language: Language) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = ShippingManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation:
            state_data = await state.get_data()
            shipping_type_dto = ShippingOptionDTO(
                name=state_data['shipping_name'],
                price=state_data['shipping_price']
            )
            shipping_type_dto = await ShippingOptionRepository.create_single(shipping_type_dto, session)
            await session.commit()
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "back_button"),
                callback_data=ShippingManagementCallback.create(0)
            )
            msg = get_text(language, BotEntity.ADMIN,
                           "shipping_option_created_successfully",
                           ).format(
                name=shipping_type_dto.name,
                price=shipping_type_dto.price,
                currency_sym=config.CURRENCY.get_localized_symbol()
            )
        else:
            await state.set_state(ShippingManagementStates.shipping_name)
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "cancel"),
                callback_data=ShippingManagementCallback.create(0)
            )
            msg = get_text(language, BotEntity.ADMIN, "request_shipping_name")
        return msg, kb_builder

    @staticmethod
    async def receive_shipping_option_data(message: Message,
                                           state: FSMContext,
                                           language: Language):
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        kb_builder = InlineKeyboardBuilder()
        current_state = await state.get_state()
        if current_state == ShippingManagementStates.shipping_name:
            await state.update_data(shipping_name=message.text)
            await state.set_state(ShippingManagementStates.shipping_price)
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "cancel"),
                callback_data=ShippingManagementCallback.create(0)
            )
            return (get_text(language, BotEntity.ADMIN,
                             "request_shipping_price").format(
                currency_sym=config.CURRENCY.get_localized_symbol()),
                    kb_builder)
        elif current_state == ShippingManagementStates.shipping_price:
            try:
                shipping_price = float(message.text)
                assert 0 < shipping_price < 1000
                await state.clear()
                await state.update_data(shipping_price=shipping_price, shipping_name=state_data['shipping_name'])
                kb_builder.button(text=get_text(language, BotEntity.COMMON, "confirm"),
                                  callback_data=ShippingManagementCallback.create(
                                      level=1,
                                      confirmation=True
                                  ))
                kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                                  callback_data=ShippingManagementCallback.create(0))
                kb_builder.adjust(1)
                return get_text(language, BotEntity.ADMIN,
                                "create_shipping_option_confirmation").format(
                    name=state_data['shipping_name'],
                    price=shipping_price,
                    currency_sym=config.CURRENCY.get_localized_symbol()
                ), kb_builder
            except Exception as _:
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "cancel"),
                    callback_data=ShippingManagementCallback.create(0)
                )
                return (get_text(language, BotEntity.ADMIN,
                                 "request_shipping_price").format(
                    currency_sym=config.CURRENCY.get_localized_symbol()),
                        kb_builder)

    @staticmethod
    async def view_all(callback: CallbackQuery,
                       session: AsyncSession,
                       language: Language) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = ShippingManagementCallback.unpack(callback.data)
        shipping_options = await ShippingOptionRepository.get_paginated(unpacked_cb.page, None, session)
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(
            text=shipping_option.name,
            callback_data=ShippingManagementCallback.create(
                level=3,
                shipping_id=shipping_option.id,
                page=unpacked_cb.page
            )
        ) for shipping_option in shipping_options]
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder,
                                                  unpacked_cb,
                                                  ShippingOptionRepository.get_max_page(None, session),
                                                  unpacked_cb.get_back_button(language, 0),
                                                  language)
        return (get_text(language, BotEntity.ADMIN, "view_all_shipping_options"),
                kb_builder)

    @staticmethod
    async def view_single(callback: CallbackQuery,
                          session: AsyncSession,
                          language: Language):
        unpacked_cb = ShippingManagementCallback.unpack(callback.data)
        shipping_option = await ShippingOptionRepository.get_by_id(unpacked_cb.shipping_id, session)
        if unpacked_cb.shipping_management_action == ShippingManagementAction.DISABLE and unpacked_cb.confirmation:
            shipping_option.is_disabled = not shipping_option.is_disabled
            await ShippingOptionRepository.update(shipping_option, session)
            await session.commit()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "disable"),
            callback_data=ShippingManagementCallback.create(
                level=3,
                shipping_management_action=ShippingManagementAction.DISABLE,
                shipping_id=shipping_option.id,
                confirmation=True,
                page=unpacked_cb.page
            )
        )
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "shipping_option_edit_name",
                          ),
            callback_data=ShippingManagementCallback.create(
                level=4,
                shipping_management_action=ShippingManagementAction.EDIT,
                shipping_type_property=ShippingOptionProperty.NAME,
                shipping_id=unpacked_cb.shipping_id
            )
        )
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "shipping_option_edit_price",
                          ),
            callback_data=ShippingManagementCallback.create(
                level=4,
                shipping_management_action=ShippingManagementAction.EDIT,
                shipping_type_property=ShippingOptionProperty.PRICE,
                shipping_id=unpacked_cb.shipping_id
            )
        )
        kb_builder.adjust(1)
        kb_builder.row(unpacked_cb.get_back_button(language))
        return get_text(language, BotEntity.ADMIN, "shipping_option_single",
                        ).format(
            id=shipping_option.id,
            name=shipping_option.name,
            currency_sym=config.CURRENCY.get_localized_symbol(),
            price=shipping_option.price,
            is_disabled=shipping_option.is_disabled
        ), kb_builder

    @staticmethod
    async def edit_property(callback: CallbackQuery,
                            state: FSMContext,
                            session: AsyncSession,
                            language: Language) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = ShippingManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation:
            state_data = await state.get_data()
            await state.clear()
            shipping_option = await ShippingOptionRepository.get_by_id(state_data['shipping_id'], session)
            shipping_option_property = ShippingOptionProperty(state_data['property'])
            shipping_option.__setattr__(shipping_option_property.name.lower(), state_data['value'])
            await ShippingOptionRepository.update(shipping_option, session)
            await session.commit()
            kb_builder.row(unpacked_cb.get_back_button(language, 0))
            return (get_text(language, BotEntity.ADMIN, "shipping_option_edited_successfully"),
                    kb_builder)
        shipping_option = await ShippingOptionRepository.get_by_id(unpacked_cb.shipping_id, session)
        property_to_edit = unpacked_cb.shipping_type_property.name.lower()
        await state.update_data(shipping_id=unpacked_cb.shipping_id, property=unpacked_cb.shipping_type_property.value)
        await state.set_state(ShippingManagementStates.edit_property)
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=ShippingManagementCallback.create(0)
        )
        return get_text(language, BotEntity.ADMIN, "request_new_property_value").format(
            current_property_value=shipping_option.__getattribute__(property_to_edit),
            property=property_to_edit.capitalize()
        ), kb_builder

    @staticmethod
    async def edit_property_confirmation(message: Message,
                                         state: FSMContext,
                                         session: AsyncSession,
                                         language: Language):
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        property_to_edit = ShippingOptionProperty(state_data['property'])
        kb_builder = InlineKeyboardBuilder()
        if property_to_edit == ShippingOptionProperty.PRICE:
            try:
                property_value = float(message.text)
                assert 0 < property_value < 1000
                await state.update_data(**state_data, value=property_value)
            except Exception as _:
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "cancel"),
                    callback_data=ShippingManagementCallback.create(0)
                )
                shipping_option = await ShippingOptionRepository.get_by_id(state_data['shipping_id'], session)
                return get_text(language, BotEntity.ADMIN, "request_new_property_value").format(
                    current_property_value=shipping_option.__getattribute__(property_to_edit.name.lower()),
                    property=property_to_edit.name.capitalize()
                ), kb_builder
        else:
            await state.update_data(**state_data, value=message.text)
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "confirm"),
            callback_data=ShippingManagementCallback.create(level=4,
                                                            confirmation=True)
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=ShippingManagementCallback.create(0)
        )
        shipping_option = await ShippingOptionRepository.get_by_id(state_data['shipping_id'], session)
        return get_text(language, BotEntity.ADMIN, "edit_shipping_property_confirmation").format(
            property=property_to_edit.name.capitalize(),
            current_property_value=shipping_option.__getattribute__(property_to_edit.name.lower()),
            new_property_value=message.text
        ), kb_builder
