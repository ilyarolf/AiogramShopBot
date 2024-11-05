# AiogramShopBot

**AiogramShopBot is a software product based on Aiogram3.x and SQLAlchemy that allows you to automate sales of digital
goods in Telegram. One of the advantages of the bot is that AiogramShopBot implements the ability to top up with
Bitcoin, Litecoin, USDT TRC-20, which allows you to sell digital goods worldwide.**

- [AiogramShopBot](#aiogramshopbot)

* [Commercial offers](#commercial-offers)
    + [Telegram. ](#-for-commercial-offers-contact-me-on-telegram)
    + [AiogramShopBotDemo](#-you-can-test-the-functionality-in-aiogramshopbotdemo).

* [1.Starting the bot](#1starting-the-bot)
    + [1.0 Description of required environment variables. ](#10-description-of-required-environment-variables)
    + [1.1 Starting AiogramShopBot without SQLCipher database encryption with Docker-compose.](#11-starting-aiogramshopbot-with-docker-compose)
    + [1.2 Starting AiogramShopBot without SQLCipher database encryption.](#12-starting-aiogramshopbot-without-sqlcipher-database-encryption)
    + [1.3 Starting AiogramShopBot with SQLCipher database encryption.](#13-starting-aiogramshopbot-with-sqlcipher-database-encryption)
* [2.AiogramShopBot User's Manual](#2aiogramshopbot-users-manual)
    + [2.1 Registration](#21-registration)
    + [2.2 Top-up balance](#22-top-up-balance)
    + [2.3 Purchase of goods](#23-purchase-of-goods)
    + [2.4 Purchase history](#24-purchase-history)
* [3.AiogramShopBot Admin Manual](#3aiogramshopbot-admin-manual)
    + [3.1 Adding a new admin](#31-adding-a-new-admin)
    + [3.2 Send to all bot users functionality](#32-send-to-all-bot-users-functionality)
    + [3.3 Adding new items to the bot](#33-adding-new-items-to-the-bot)
    + [3.4 Send to everyone restocking message](#34-send-to-everyone-restocking-message)
    + [3.5 Get new users](#35-get-new-users)
    + [3.6 Delete categories and subcategories](#36-delete-categories-and-subcategories)
    + [3.7 Make refund](#37-make-refund)
    + [3.8 Admin notifications](#38-admin-notifications)

    - [3.8.1 Notification to admin about new deposit](#381-notification-to-admin-about-new-deposit)
    - [3.8.2 Notification to admin about new buy](#382-notification-to-admin-about-new-buy)
* [4.0 Multibot (Experimental functionality)](#40-multibot-experimental-functionality)
    + [4.1 Starting the multibot](#41-starting-the-multibot)
* [📋 Todo List](#-todo-list)
* [✨ DONATE Buy Me Coffee](#-donate-buy-me-coffee)
* [MIT License](LICENSE)

## 📌Commercial offers

### ➤ For commercial offers contact me on [Telegram](https://t.me/ilyarolf_dev).
### 🤖 You can test the functionality in [AiogramShopBotDemo](https://t.me/demo_aiogramshopbot).

## 1.Starting the bot

### 1.0 Description of required environment variables

| Environment Variable Name | Description                                                                                                                                                                                                                                                                                                                 | Recommend Value                                                     |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| WEBHOOK_PATH              | The path to the webhook where Telegram servers send requests for bot updates. It is not recommended to change it if only one bot will be deployed. In case several bots will be deployed on the same server, it will be necessary to change it, because there will be path collision (Does not apply to the multibot case). | "" (empty string)                                                   |
| WEBAPP_HOST               | Hostname for Telegram bot, it is not recommended to change in case you use docker-compose.                                                                                                                                                                                                                                  | For docker-compose="0.0.0.0".<br/>For local deployment="localhost". |
| WEBAPP_PORT               | Port for Telegram bot, if you plan to deploy several bots on the same server, you will need to assign a different port to each one (Not relevant to the multibot case).                                                                                                                                                     | No recommended value                                                |
| TOKEN                     | Token from your Telegram bot, you can get it for free in Telegram from the bot of all bots with the username @botfather.                                                                                                                                                                                                    | No recommended value                                                |
| NGROK_TOKEN               | Token from your NGROK profile, it is needed for port forwarding to the Internet. The main advantage of using NGROK is that NGROK assigns the HTTPS certificate for free.                                                                                                                                                    | No recommended value                                                |
| ADMIN_ID_LIST             | List of Telegram id of all admins of your bot. This list is used to check for access to the admin menu.                                                                                                                                                                                                                     | No recommended value                                                |
| SUPPORT_LINK              | A link to the Telegram profile that will be sent by the bot to the user when the “Help” button is pressed.                                                                                                                                                                                                                  | https://t.me/${YOUR_USERNAME_TG}                                    |
| DB_NAME                   | The name of the SQLite database file.                                                                                                                                                                                                                                                                                       | database.db                                                         |
| PAGE_ENTIRES              | The number of entries per page. Serves as a variable for pagination.                                                                                                                                                                                                                                                        | 8                                                                   |
| BOT_LANGUAGE              | The name of the .json file with the l10n localization. At the moment only English localization is supplied out of the box, but you can make your own if you create a file in the l10n folder with the same keys as in l10n/en.json.                                                                                         | "en"                                                                |
| MULTIBOT                  | Experimental functionality, allows you to raise several bots in one process. And there will be one main bot, where you can create other bots with the command “/add $BOT_TOKEN”. Accepts string parameters “true” or “false”.                                                                                               | "false"                                                             |
| DB_PASS                   | Only works in the feature/sqlalchemy-sqlcipher branch. The password that will be used to encrypt your SQLite database.                                                                                                                                                                                                      | No recommended value                                                |

### 1.1 Starting AiogramShopBot with Docker-compose.

* Clone the project from the master branch.<br>``git clone git@github.com:ilyarolf/AiogramShopBot.git``
* If you want to use the version with database encryption, clone from the feature/sqlalchemy-sqlcipher
  branch.<br>``git clone git@github.com:ilyarolf/AiogramShopBot.git -b feature/sqlalchemy-sqlcipher``
* Set environment variables in docker-compose.yml file, token from @BotFather(``TOKEN``), token from
  ngrok(``NGROK_TOKEN``), telegram id of admins(``ADMIN_ID_LIST``), support link (``SUPPORT_LINK``, the link will be
  needed for the "Help" button in the bot).
* If you use the version with database encryption, you must set a variable with the password from the
  database (``DB_PASS``).
* Run the ``docker-compose up`` command.

> **Note**
> **<br>To get the ngrok token, you need to register on the ngrok website and confirm your email. Then you will have the
ngrok token in your personal account.**

### 1.2 Starting AiogramShopBot without SQLCipher database encryption.

> **Note**
> **<br>Fully compatible with python 3.9.6.<br>AiogramShopBot from the master branch does not use database encryption
via SQLCipher, but it does use Aiosqlite**

* Clone the project from the master branch. ``git clone git@github.com:ilyarolf/AiogramShopBot.git``
* Install all necessary packages ``pip install -r requirements.txt``
* Set the environment variables to run in the .env file.<br>Example:

```
WEBHOOK_PATH = "/bot"
WEBAPP_HOST = "localhost"
WEBAPP_PORT = 1234
TOKEN = "TELEGRAM_BOT_TOKEN_HERE"
ADMIN_ID_LIST = 123456,654321
SUPPORT_LINK = "https://t.me/your_username_123"
DB_NAME = "db_file_name.db"
NGROK_TOKEN = "NGROK_TOKEN_HERE"
PAGE_ENTRIES = 8
BOT_LANGUAGE = "en"
MULTIBOT = "false"
```

* After these steps the bot is ready to run, the entry point to run the bot is run.py ```python run.py```

### 1.3 Starting AiogramShopBot with SQLCipher database encryption.

> **Note**
> **<br>To run AiogramShopBot with database encryption via SQLCipher, it is recommended to use Linux kernel operating
systems because installing SQLCipher on Windows is not the easiest.**

* Clone the project from the feature/sqlalchemy-sqlcipher
  branch.<br>``git clone git@github.com:ilyarolf/AiogramShopBot.git -b feature/sqlalchemy-sqlcipher``
* Install the SQLCipher package, for example in Ubuntu this can be done with the command ``sudo apt install sqlcipher``.
* Install all necessary packages ``pip install -r requirements.txt``
* Variables in .env are set in the same way as in point 1.1, but with one exception, you need to set a password for the
  database.<br>Example:

```
WEBHOOK_PATH = "/bot"
WEBAPP_HOST = "localhost"
WEBAPP_PORT = 1234
TOKEN = "TELEGRAM_BOT_TOKEN_HERE"
ADMIN_ID_LIST = 123456,654321
SUPPORT_LINK = "https://t.me/your_username_123"
DB_NAME = "db_file_name.db"
DB_PASS = "your_password_to_database"
NGROK_TOKEN = "NGROK_TOKEN_HERE"
PAGE_ENTRIES = 8
BOT_LANGUAGE = "en"
MULTIBOT = "false"
```

* After these steps the bot is ready to run, the entry point to run the bot is run.py ```python run.py```

## 2.AiogramShopBot User's Manual

### 2.1 Registration

User registration occurs when the bot is first accessed with the ``/start`` command. Each user is assigned a different
mnemonic phrase to generate BTC, LTC, USDT TRC20 crypto addresses. BTC and LTC addresses are generated according to
BIP-84 standard, for USDT TRC20 the BIP-44 standard is used, this is done so that wallets can be easily imported into
Trust Wallet.

### 2.2 Top-up balance

To deposit balance in the bot, go to "My Profile -> Top Up balance". Copy the address of the cryptocurrency you want to
top up and send the cryptocurrency there, then go back to "My Profile" and click "Refresh Balance". Refreshing the
balance takes some time (1-2 seconds).
<br>![img](https://i.imgur.com/THwsPIv.png)
> **Note**
> "Refresh balance" button has a 30 second cooldown.

### 2.3 Purchase of goods

To buy any item, go to "All categories" -> Select any category -> Select any subcategory -> Select quantity -> Confirm
purchase. If the purchase is successful, you will immediately receive a message in the format:
![img](https://i.imgur.com/RSrqMjt.png)

### 2.4 Purchase history

* To access your purchase history go to "My Profile" -> "Purchase History".
* You will be presented with an inline keyboard with all your purchases, by clicking on any of the purchases you will be
  sent a message in the format from paragraph 2.3.
  ![imb](https://i.imgur.com/tz92b4q.png)

## 3.AiogramShopBot Admin Manual

### 3.1 Adding a new admin

To add a new admin you need to add his telegram id to the ADMIN_ID_LIST environment variable, separated by commas, and
reload the bot.<br>For example: ``ADMIN_ID_LIST=123456,654321``

### 3.2 Send to all bot users functionality

* Open the admin panel by entering the command ``/admin``, then click on the "Send to everyone" button.
* Type a message or forward to the bot, the bot supports sending a message with pictures and Telegram markup (bold,
  italics, spoilers, etc.).
* Confirm or decline the sending of messages.
* After successful message sending, the original message with inline buttons "Confirm", "Decline" will change
  to this.<br>
  ![img](https://i.imgur.com/Jy5pXLe.png)

### 3.3 Adding new items to the bot

> **Note**
> The functionality for adding new products so far supports adding products using .json files.

* Open the admin panel by entering the command ``/admin``.
* Click on the "Add new items" button.
* Send .json file with new items.<br>Example of .json file:

```
{
	"items": [
		{
			"category": "Category#1",
			"subcategory": "Subcategory#1",
			"price": 50,
			"description": "Mocked description",
			"private_data": "Mocked private data"
		},
		{
			"category": "Category#2",
			"subcategory": "Subcategory#2",
			"price": 100,
			"description": "Mocked description",
			"private_data": "Mocked private data"
		}
	]
}
```

> **Note**
> The "private_data" property is what the user gets when they make a purchase.

### 3.4 Send to everyone restocking message

* Open the admin panel by entering the command ``/admin``.
* Click on the "Send restocking message" button.

> **Note**
> Restocking message is generated automatically and looks as follows:

![img](https://i.imgur.com/LeHcEhC.png)

### 3.5 Statistics

* Open the admin panel by sending a message to the bot with the command “/admin”.
* Click on the “Statistics” button.
* The bot will send you a message about selecting an entity to build statistics, at the moment it is suggested to build
  statistics on purchases and new users.<br>
  ![img](https://i.imgur.com/QVFTdpZ.png)
* The bot will send you a message with three buttons, select the time delta, i.e. for which time period to build
  statistics. At the moment it offers to build statistics for the last day, last 7 days and last month.<br>
  ![img](https://i.imgur.com/mu198lh.png)
* After selecting the entity and time delta, the bot will send you a message with statistics.<br>
  ![img](https://i.imgur.com/Yo58XqM.png)

### 3.6 Delete categories and subcategories

* Open the admin panel by entering the command ``/admin``.
* Click on the ``Delete category`` or ``Delete subcategory`` button.
* Select a category or subcategory, confirm deletion. If the deletion is successful, you will receive the
  message ``Sucessfully deleted {name} category/subcategory``

### 3.7 Make refund

> **Note**
> Refunds returns money to the user's balance in the bot.

* Open the admin panel by entering the command ``/admin``.
* Click on the ``Make refund`` button.
* In the received message you will have inline buttons in the
  format ``TelegramID/TelegramUsername|TotalPrice|SubcategoryName``.<br>For
  example: ``@durov|$500.0|Test subcategory``.<br>
  ![img](https://i.imgur.com/62zU5AU.png)
* Select the purchase for which you want to make a refund.
* You will receive a message
  in ``Do you really want to refund user @durov for purchasing 1 SubcategoryName in the amount of $500.0`` format.
  Confirm or decline the refund.<br>
  ![img](https://i.imgur.com/eacELis.png)
* If the refund is successful, you will receive
  a ``Successfully refunded $500.0 to user durov for purchasing 1 SubcategoryName`` message.
  <br>![img](https://i.imgur.com/pa4Qj4Z.png)
* The user to whom you returned the message will also receive a message
  in ``You have been refunded $50.0 for the purchase of 1 pieces of SubcategoryName`` format.
  <br>![img](https://i.imgur.com/dOeqOJL.png)

### 3.8 Admin notifications

> **Note**
> All users with telegram id in the .env ADMIN_ID_LIST environment variable will receive these notifications

#### 3.8.1 Notification to admin about new deposit

* If any user topped up the balance and clicked on the "Refresh balance" button, you will receive the following message
  from the bot:

<br>![img](https://i.imgur.com/Vu3aKzt.png)

#### 3.8.2 Notification to admin about new buy

After each purchase, you will receive a message in the format:

<br>![img](https://i.imgur.com/i9EQF9I.png)

## 4.0 Multibot (Experimental functionality)

### 4.1 Starting the multibot

* Set all environment variables in docker-compose.yml and set the variable “true” for MULTIBOT.
  ``MULTIBOT="true"``
* Run the ``docker-compose up`` command.
* After successful execution of the command, you will only deploy a manager bot for other bots, it will not have
  functionality for buying items etc. To deploy a bot with functionality to sell goods etc, you need to send the
  command ``/add $TOKEN`` to the bot manager. If everything is successful, you will receive this notification.
  ![img](https://i.imgur.com/YAGjN3G.png)

## 📋 Todo List

- [x] Make migration from direct raw database queries to SQLAlchemy ORM.
- [x] Add option to encrypt database via SQLCipher (when using SQLAlchemy).
- [x] Add an option to generate new crypto addresses using new mnemonic phrases so that 1 user=1 mnemonic phrase.
- [x] Items pagination.
- [x] Make the functionality of database backup by action in the admin in the Telegram bot.
- [x] Make the functionality of generating statistics of sales and users in the bot for a month/week/day in the admin
  panel.
- [ ] Make the functionality of generating statistics of deposits in the bot for a month/week in the admin
  panel.

## ✨ DONATE Buy Me Coffee

* BTC - bc1q2kv89q8yvf068xxw3x65gzfag98l9wnrda3x56
* LTC - ltc1q0tuvm5vqn9le5zmhvhtp7z9p2eu6yvv24ey686
* TRX - THzRw8UpTsEYBEG5CCbsCVnJzopSHFHJm6
* SOL - Avm7VAqPrwpHteXKfDTRFjpj6swEzjmj3a2KQvVDvugK
* ETH - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* USDT ERC20 - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* USDT BEP20 - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* USDT TRC20 - THzRw8UpTsEYBEG5CCbsCVnJzopSHFHJm6
