from enums.bot_entity import BotEntity
from enums.language import Language
from models.item import ItemDTO
from utils.utils import get_text


class MessageService:
    @staticmethod
    def create_message_with_bought_items(items: list[ItemDTO], language: Language):
        message = "<b>"
        for count, item in enumerate(items, start=1):
            private_data = item.private_data
            message += get_text(language, BotEntity.USER, "purchased_item").format(count=count,
                                                                                   private_data=private_data)
        message += "</b>\n"
        return message
