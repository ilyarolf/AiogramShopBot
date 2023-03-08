from json import load
from os import remove


class FileRequests:
    """Класс для работы с файлами"""
    def get_user_count(self) -> int:
        """Функция для полученя номера пользователя"""
        with open("users_count_shop.txt", "r") as users:
            users_count = int(users.read())
        temp_users_count = str(users_count + 1)
        with open("users_count_shop.txt", "w") as users:
            users.write(temp_users_count)
            del temp_users_count
        return users_count

    def get_wallets(self) -> list:
        """ Функция возвращает btc,ltc,trx адреса в виде списка для номера пользователя user_count"""
        user_wallets = []
        names = ['btc', 'ltc', 'trx']
        user_count = self.get_user_count()
        for name in names:
            with open(f"{name}.txt", "r") as wallets:
                lines = wallets.readlines()
                user_wallets.append(lines[user_count])
        return user_wallets

    def get_new_items(self, filename: str):
        """Функция для распарсинга json файла с новыми товарами"""
        with open(filename, 'r') as file:
            file_json = load(file)
            category = file_json['category']
            subcategory = file_json['subcategory']
            data = file_json['data']
            price = file_json['price']
            description = file_json['description']
            item_list = []
            for item in data:
                item = item['private_data']
                item_list.append(item)
        remove(filename)
        return item_list, category, subcategory, price, description
