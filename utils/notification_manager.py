from bot import bot
from utils.other_sql import RefundBuyDTO


class NotificationManager:
    @staticmethod
    async def send_refund_message(refund_data: RefundBuyDTO):
        message = f"You have been refunded ${refund_data.total_price} for the purchase of {refund_data.quantity}" \
                  f" pieces of {refund_data.subcategory}"
        try:
            await bot.send_message(refund_data.telegram_id, f"<b>{message}</b>", parse_mode="html")
        except Exception:
            pass
