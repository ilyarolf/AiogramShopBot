from enums.bot_entity import BotEntity
from models.item import ItemDTO
from utils.localizator import Localizator


class MessageService:
    @staticmethod
    def create_message_with_bought_items(items: list[ItemDTO]):
        message = "<b>"
        for count, item in enumerate(items, start=1):
            private_data = item.private_data
            message += Localizator.get_text(BotEntity.USER, "purchased_item").format(count=count,
                                                                                     private_data=private_data)
        message += "</b>\n"
        return message
