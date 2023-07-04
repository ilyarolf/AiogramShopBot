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
            with open(f"wallets/{name}.txt", "r") as wallets:
                lines = wallets.readlines()
                user_wallets.append(lines[user_count])
        return user_wallets

    def get_new_items(self, filename: str) -> dict:
        """Функция для распарсинга json файла с новыми товарами"""
        with open(filename, 'r') as file:
            output_dict = dict()
            file_json = load(file)
            bulk = file_json['bulk']
            for i in range(len(bulk)):
                position = bulk[i]
                item_list = []
                category = position['category']
                subcategory = position['subcategory']
                data = position['data']
                price = position['price']
                description = position['description']
                for item in data:
                    item = item['private_data']
                    item_list.append(item)
                output_dict[i] = (item_list, category, subcategory, price, description)
        remove(filename)
        # return item_list, category, subcategory, price, description
        return output_dict

    def get_new_freebies(self, filename: str) -> dict:
        """Функция для распарсинга json файла с халявой"""
        with open(filename, 'r', encoding='utf-8') as file:
            output_dict = dict()
            freebies = load(file)['freebies']
            for item in freebies:
                output_dict.update(item)
        remove(filename)
        return output_dict
