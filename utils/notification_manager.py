from CryptoAddressGenerator import CryptoAddressGenerator
from bot import bot
from config import ADMIN_ID_LIST
from models.user import User
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

    @staticmethod
    async def send_to_admins(message: str):
        for admin_id in ADMIN_ID_LIST:
            try:
                await bot.send_message(admin_id, f"<b>{message}</b>", parse_mode='html')
            except Exception:
                pass

    @staticmethod
    async def new_deposit(old_crypto_balances: dict, new_crypto_balances: dict, deposit_amount_usd, telegram_id: int):
        merged_crypto_balances = [new_balance - old_balance for (new_balance, old_balance) in
                                  zip(new_crypto_balances.values(),
                                      old_crypto_balances.values())]
        merged_crypto_balances_keys = [key.split('_')[0] for key in new_crypto_balances.keys()]
        merged_crypto_balances = zip(merged_crypto_balances_keys, merged_crypto_balances)
        user = User.get_by_tgid(telegram_id)
        username = user['telegram_username']
        if username:
            message = f"New deposit by user with username @{username} for ${deposit_amount_usd} with:"
        else:
            message = f"New deposit by user with ID {telegram_id} for ${deposit_amount_usd} with:"
        private_keys = CryptoAddressGenerator().get_private_keys(user['user_id'])
        for crypto_name, value in merged_crypto_balances:
            if value > 0:
                message += f"\n{round(value, 2)} {crypto_name.upper}\nPrivate key:<code>{private_keys[crypto_name]}</code>"
                #TODO("Doesn't work after round(value, 2) and <code></code>")
        await NotificationManager.send_to_admins(message)
