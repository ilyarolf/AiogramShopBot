from enums.bot_entity import BotEntity
from models.item import ItemDTO
from utils.localizator import Localizator
import config


class MessageService:
    @staticmethod
    def create_message_with_bought_items(items: list[ItemDTO]):
        message = "<b>"
        for count, item in enumerate(items, start=1):
            private_data = item.private_data
            description = item.description or "Item"
            message += Localizator.get_text(BotEntity.USER, "purchased_item").format(
                count=count,
                description=description,
                private_data=private_data
            )
        message += "</b>\n"

        # Add data retention notice
        message += Localizator.get_text(BotEntity.USER, "purchased_items_retention_notice").format(
            retention_days=config.DATA_RETENTION_DAYS
        )

        return message
