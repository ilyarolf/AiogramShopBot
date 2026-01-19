<h1 align="center">AiogramShopBot</h1>

<p align="center">
  <a href="https://t.me/demo_aiogramshopbot">
    <img src="https://img.shields.io/badge/Live_Demo_Bot-blue?logo=probot&logoColor=white" alt="Live bot"/>
  </a>
  <a href="https://t.me/ilyarolf_dev">
    <img src="https://img.shields.io/badge/Contact_me-blue?logo=telegram&logoColor=white" alt="Business_offer"/>
  </a>
</p>


[![Python](https://img.shields.io/badge/Python_3.12-3776AB?logo=python&logoColor=%23fff)](https://www.python.org/downloads/release/python-3127/)
[![Dockerhub](https://img.shields.io/badge/Docker_Hub-2496ED?logo=docker&logoColor=fff)](https://hub.docker.com/r/ilyarolf/aiogram-shop-bot)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)](https://www.sqlite.org/)
[![Bitcoin](https://img.shields.io/badge/Bitcoin-FF9900?logo=bitcoin&logoColor=white)](https://github.com/bitcoin/bitcoin)
[![Litecoin](https://img.shields.io/badge/Litecoin-A6A9AA?logo=litecoin&logoColor=white)](https://github.com/litecoin-project/litecoin)
[![Solana](https://img.shields.io/badge/Solana-9945FF?logo=solana&logoColor=fff)](https://github.com/solana-labs/solana)
[![Ethereum](https://img.shields.io/badge/Ethereum-3C3C3D?logo=ethereum&logoColor=white)](https://github.com/ethereum)
[![BinanceCoin](https://img.shields.io/badge/Binance-FCD535?logo=binance&logoColor=000)](https://github.com/binance)

**AiogramShopBot is a software product based on Aiogram3, SQLAlchemy, and SQLAdmin that allows you to automate the sale of digital and physical goods in Telegram. One of the advantages of the bot is that AiogramShopBot implements the ability to replenish funds using Bitcoin, Litecoin, Solana, Ethereum, and Binance Coin, which allows you to sell goods worldwide.<br>
The bot implements the most popular features: a referral system, a review feature, a web admin panel for working with database objects, multiple i18n localization, and much more.**

---

* [🤝 Commercial offers](#commercial-offers)
    + [➤ Telegram. ](#-for-commercial-offers-contact-me-on-telegram)
    + [🤖 AiogramShopBotDemo](#-you-can-test-the-functionality-in-aiogramshopbotdemo).
* [✨ Donate](#donate-)
* [1.Launch the bot](#1starting-the-bot)
    + [1.0 Description of required environment variables. ](#10-description-of-required-environment-variables)
    + [1.1 Quick start.](#11-quick-start)
    + [1.2 Launch AiogramShopBot without SQLCipher database encryption.](#12-starting-aiogramshopbot-locally)
* [2. 👥 AiogramShopBot User's Manual](#2aiogramshopbot-users-manual)
    + [2.1 🖥️ Registration](#21-registration)
    + [2.2 ➕ Top Up Balance](#22--top-up-balance)
    + [2.3 👜 Purchase of goods](#23-purchase-of-goods)
    + [2.4 🧾 Purchase History](#24--purchase-history)
* [3. 🔑 AiogramShopBot Admin Manual](#3aiogramshopbot-admin-manual)
    + [3.1 🔑 Adding a new admin](#31-adding-a-new-admin)
    + [3.2 📢 Announcements](#32--announcements)
        - [3.2.1 📢 Send to Everyone](#321--send-to-everyone)
        - [3.2.2 🔄 Restocking Message](#322--restocking-message)
        - [3.2.3 🗂️ Current Stock](#323--current-stock)
    + [3.3 📦 Inventory Management](#33--inventory-management)
        - [3.3.1 ➕ Add Items](#331--add-items)
            - [3.3.1.1 JSON](#3311-json)
            - [3.3.1.2 TXT](#3312-txt)
    + [3.4 👥 User Management](#34--user-management)
        - [3.4.1 💳 Credit Management](#341--credit-management)
            - [3.4.1.1 ➕ Add balance](#3411--add-balance)
            - [3.4.1.2 ➖ Reduce balance](#3412--reduce-balance)
        - [3.4.2 ↩️ Make Refund](#342--make-refund)
    + [3.5 📊 Analytics & Reports](#35--analytics--reports)
        - [3.5.1 📊 Statistics](#351--statistics)
    + [3.6 🔔 Admin notifications](#36--admin-notifications)
        - [3.6.1 Notification to admin about new deposit](#361-notification-to-admin-about-new-deposit)
        - [3.6.2 Notification to admin about new buy](#362-notification-to-admin-about-new-buy)
    + [3.8 👛 Wallet](#38--wallet)
        - [3.8.1 Cryptocurrency withdrawal](#381-cryptocurrency-withdrawal-functionality)
    + [3.9 📷 Media management](#39--media-management)
    + [3.10 🎪 Coupons management](#310--coupons-management)
        - [3.10.1 🎫 Create new coupon](#3101--create-new-coupon)
        - [3.10.2 📋 View all coupons](#3102--view-all-coupons)
    + [3.11 📦 Shipping management](#311--shipping-management)
        - [3.11.1 🚚 Create new shipping option](#3111--create-new-shipping-option)
        - [3.11.2 📋 View all shipping options](#3112--view-all-shipping-options)
    + [3.12 🛍 Buys management](#312--buys-management)
    + [3.13 ⭐ Reviews Management](#313--reviews-management)
* [4.0 Cryptocurrency Forwarding ](#40-cryptocurrency-forwarding-)
* [5.0 Referral System](#50-referral-system)
    + [5.1 Access to the Referral System](#51-access-to-the-referral-system)
    + [5.2 How Referrals Work](#52-how-referrals-work)
    + [5.3 Referral Bonuses (Referred User)](#53-referral-bonuses-referred-user)
    + [5.4 Referrer Bonuses (Inviting User)](#54-referrer-bonuses-inviting-user)
    + [5.5 Global Bonus Cap](#55-global-bonus-cap)
    + [5.6 Anti-Abuse Guarantees](#56-anti-abuse-guarantees)
* [6.0 Admin panel with web interface (SQLAdmin)](#60-admin-panel-with-web-interface-sqladmin)
* [7.0 Multibot (Experimental functionality)](#70-multibot-experimental-functionality)
    + [5.1 Starting the multibot](#71-starting-the-multibot)
* [📋 Todo List](#-todo-list)
* [MIT License](LICENSE)

## 📌Commercial offers

### ➤ For commercial offers contact me on [Telegram](https://t.me/ilyarolf_dev).

### 🤖 You can test the functionality in [AiogramShopBotDemo](https://t.me/demo_aiogramshopbot).

## Donate ✨

* BTC - bc1q2kv89q8yvf068xxw3x65gzfag98l9wnrda3x56
* LTC - ltc1q0tuvm5vqn9le5zmhvhtp7z9p2eu6yvv24ey686
* TRX - THzRw8UpTsEYBEG5CCbsCVnJzopSHFHJm6
* SOL - Avm7VAqPrwpHteXKfDTRFjpj6swEzjmj3a2KQvVDvugK
* ETH - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* TON - UQD0QetwXoYTsmbZWVbE_z_JUFh54RVVRUxCbCHQkLsl3Hfn
* USDT ERC20 - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* USDT BEP20 - 0xB49D720DE2630fA4C813d5B4c025706E25cF74fe
* USDT TRC20 - THzRw8UpTsEYBEG5CCbsCVnJzopSHFHJm6

---

## 1.Starting the bot

### 1.0 Description of required environment variables

| Environment Variable Name    | Description                                                                                                                                                                                                                                                                                                                 | Recommend Value                                                     |
|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| WEBHOOK_PATH                 | The path to the webhook where Telegram servers send requests for bot updates. It is not recommended to change it if only one bot will be deployed. In case several bots will be deployed on the same server, it will be necessary to change it, because there will be path collision (Does not apply to the multibot case). | "/"                                                                 |
| WEBAPP_HOST                  | Hostname for Telegram bot, it is not recommended to change in case you use docker-compose.                                                                                                                                                                                                                                  | For docker-compose="0.0.0.0".<br/>For local deployment="localhost". |
| WEBAPP_PORT                  | Port for Telegram bot, if you plan to deploy several bots on the same server, you will need to assign a different port to each one (Not relevant to the multibot case).                                                                                                                                                     | 5000                                                                |
| TOKEN                        | Token from your Telegram bot, you can get it for free in Telegram from the bot of all bots with the username @botfather.                                                                                                                                                                                                    | No recommended value                                                |
| ADMIN_ID_LIST                | List of Telegram id of all admins of your bot. This list is used to check for access to the admin menu.                                                                                                                                                                                                                     | No recommended value                                                |
| SUPPORT_LINK                 | A link to the Telegram profile that will be sent by the bot to the user when the “Help” button is pressed.                                                                                                                                                                                                                  | https://t.me/${YOUR_USERNAME_TG}                                    |
| POSTGRES_USER                | PostgreSQL username.                                                                                                                                                                                                                                                                                                        | postgres                                                            |
| POSTGRES_PASSWORD            | PostgreSQL password.                                                                                                                                                                                                                                                                                                        | Any string you want                                                 |
| DB_PORT                      | PostgreSQL port.                                                                                                                                                                                                                                                                                                            | 5432                                                                |
| DB_HOST                      | PostgreSQL host.                                                                                                                                                                                                                                                                                                            | postgres                                                            |
| NGROK_TOKEN                  | Token from your NGROK profile, it is needed for port forwarding to the Internet. The main advantage of using NGROK is that NGROK assigns the HTTPS certificate for free.                                                                                                                                                    | No recommended value                                                |
| PAGE_ENTRIES                 | The number of entries per page. Serves as a variable for pagination.                                                                                                                                                                                                                                                        | 8                                                                   |
| MULTIBOT                     | Experimental functionality, allows you to raise several bots in one process. And there will be one main bot, where you can create other bots with the command “/add $BOT_TOKEN”. Accepts string parameters “true” or “false”.                                                                                               | "false"                                                             |
| CURRENCY                     | Currency to be used in the bot.                                                                                                                                                                                                                                                                                             | "USD" or "EUR" or "JPY" or "CAD" or "GBP"                           |
| RUNTIME_ENVIRONMENT          | If set to "dev", the bot will be connected via an ngrok tunnel. "prod" will use [Caddy](https://hub.docker.com/r/lucaslorentz/caddy-docker-proxy) as reverse proxy together with your public hostname                                                                                                                       | "prod" or "dev"                                                     |   
| WEBHOOK_SECRET_TOKEN         | Required variable, used to protect requests coming from Telegram servers from spoofing.                                                                                                                                                                                                                                     | Any string you want                                                 |   
| KRYPTO_EXPRESS_API_KEY       | API KEY from KryptoExpress profile                                                                                                                                                                                                                                                                                          | No recommended value                                                |   
| KRYPTO_EXPRESS_API_URL       | API URL from KryptoExpress service                                                                                                                                                                                                                                                                                          | https://KryptoExpress.pro/api                                       |   
| KRYPTO_EXPRESS_API_SECRET    | Required variable, used to protect requests coming from KryptoExpress servers from spoofing.                                                                                                                                                                                                                                | Any string you want                                                 |   
| REDIS_PASSWORD               | Required variable, needed to make the throttling mechanism work.                                                                                                                                                                                                                                                            | Any string you want                                                 |   
| REDIS_HOST                   | Required variable, needed to make the throttling mechanism work.                                                                                                                                                                                                                                                            | "redis" for docker-compose.yml                                      |   
| CRYPTO_FORWARDING_MODE       | Optional variable, when CRYPTO_FORWARDING_MODE is enabled, all deposits are automatically transferred to your addresses.                                                                                                                                                                                                    | "true" or "false"                                                   |   
| BTC_FORWARDING_ADDRESS       | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true, BECH32 format only.                                                                                                                                                                                                                                            | BECH32 format only.                                                 |   
| LTC_FORWARDING_ADDRESS       | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true. BECH32 format only.                                                                                                                                                                                                                                            | BECH32 format only.                                                 |   
| ETH_FORWARDING_ADDRESS       | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true.                                                                                                                                                                                                                                                                | Ethereum address.                                                   |   
| SOL_FORWARDING_ADDRESS       | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true.                                                                                                                                                                                                                                                                | Solana address.                                                     |   
| BNB_FORWARDING_ADDRESS       | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true.                                                                                                                                                                                                                                                                | Binance-Coin address.                                               |   
| MIN_REFERRER_TOTAL_DEPOSIT   | Optional variable, mandatory if CRYPTO_FORWARDING_MODE=true.                                                                                                                                                                                                                                                                | "500"                                                               |   
| REFERRAL_BONUS_PERCENT       | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "5"                                                                 |   
| REFERRAL_BONUS_DEPOSIT_LIMIT | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "3"                                                                 |   
| REFERRER_BONUS_PERCENT       | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "3"                                                                 |   
| REFERRER_BONUS_DEPOSIT_LIMIT | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "5"                                                                 |   
| REFERRAL_BONUS_CAP_PERCENT   | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "7"                                                                 |   
| REFERRER_BONUS_CAP_PERCENT   | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "7"                                                                 |   
| TOTAL_BONUS_CAP_PERCENT      | A mandatory variable for the referral system to work.                                                                                                                                                                                                                                                                       | "12"                                                                |   
| SQLADMIN_RAW_PASSWORD        | Required variable for SQLAdmin to work.                                                                                                                                                                                                                                                                                     | A random string of 32 characters.                                   |   
| JWT_EXPIRE_MINUTES           | Required variable for generating a JWT token.                                                                                                                                                                                                                                                                               | "30"                                                                |   
| JWT_ALGORITHM                | Required variable for generating a JWT token.                                                                                                                                                                                                                                                                               | "HS256"                                                             |   
| JWT_SECRET_KEY               | Required variable for generating a JWT token.                                                                                                                                                                                                                                                                               | A random string of 32 characters.                                   |   

### 1.1 Quick start.
Connect to your VPS via SSH and run this command.
An interactive script will prompt you for variables for .env.
```
sudo sh -c "$(curl -fsSL https://raw.githubusercontent.com/ilyarolf/AiogramShopBot/refs/heads/master/scripts/deploy.sh)"
```

---

#### Development and production mode

For local development on a computer which is not internet facing, set the "RUNTIME_ENVIRONMENT" to "dev". The bot will
be connected via an ngrok tunnel.
> **⚠️ Note**<br>
> **To get the ngrok token, you need to register on the ngrok website and confirm your email. Then you will have the
ngrok token in your personal account.<br>You will still need Redis.**

On an internet facing production system you can either set your own hostname in the caddy label (in the template shown
with "YOUR_DOMAIN_GOES_HERE"
or make use of services
like [sslip.io](https://sslip.io/). [Caddy](https://hub.docker.com/r/lucaslorentz/caddy-docker-proxy) will automatically
pull a TLS certificate
and serves as reverse proxy for your bot. You can also run your bot together with an already existing reverse proxy. In
this case you have to remove the caddy service from the docker-compose file and configure the reverse proxy accordingly.

---

### 1.2 Starting AiogramShopBot locally.
> **⚠️ Note**<br>
> **Please note that in order to deploy the bot locally, you must have a reverse proxy, Redis, and PostgreSQL configured.**

* Clone the project from the master branch. <br>``git clone https://github.com/ilyarolf/AiogramShopBot.git``
* Install all necessary packages <br>``pip install -r requirements.txt``
* Set the environment variables to run in the .env file.<br>Example:

```
WEBHOOK_PATH = "/"
WEBAPP_HOST = "localhost"
WEBAPP_PORT = 5000
TOKEN = "1234567890:QWER.....TYI"
ADMIN_ID_LIST = 123456,654321
SUPPORT_LINK = "https://t.me/your_username_123"
POSTGRES_USER = "postgres"
DB_ENCRYPTION = "false"
POSTGRES_PASSWORD = "qwertyu"
DB_PORT = "5432"
DB_HOST = "localhost"
POSTGRES_DB = "aiogram-shop-bot"
NGROK_TOKEN = "NGROK_TOKEN_HERE"
PAGE_ENTRIES = "8"
MULTIBOT = "false"
CURRENCY = "USD"
RUNTIME_ENVIRONMENT = "PROD"
WEBHOOK_SECRET_TOKEN = "1234567890"
KRYPTO_EXPRESS_API_KEY = "API_KEY_HERE"
KRYPTO_EXPRESS_API_URL = "https://kryptoexpress.pro/api"
KRYPTO_EXPRESS_API_SECRET = "1234567890"
REDIS_PASSWORD = "1234567890"
REDIS_HOST = "localhost"
CRYPTO_FORWARDING_MODE = "false"
BTC_FORWARDING_ADDRESS = ""
LTC_FORWARDING_ADDRESS = ""
ETH_FORWARDING_ADDRESS = ""
SOL_FORWARDING_ADDRESS = ""
BNB_FORWARDING_ADDRESS = ""
MIN_REFERRER_TOTAL_DEPOSIT = "500"
REFERRAL_BONUS_PERCENT = "5"
REFERRAL_BONUS_DEPOSIT_LIMIT = "3"
REFERRER_BONUS_PERCENT = "3"
REFERRER_BONUS_DEPOSIT_LIMIT = "5"
REFERRAL_BONUS_CAP_PERCENT = "7"
REFERRER_BONUS_CAP_PERCENT = "7"
TOTAL_BONUS_CAP_PERCENT = "12"
SQLADMIN_RAW_PASSWORD = "admin"
JWT_EXPIRE_MINUTES = "30"
JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = "1234567890"
```

* After these steps the bot is ready to run, launch the bot with command ```python run.py```

---

## 2.AiogramShopBot User's Manual

---

### 2.1 Registration

User registration occurs when the bot is first accessed with the ``/start`` command.

---

### 2.2 ➕ Top Up Balance

* Open my profile menu using the <u>“👤 My profile”</u> button.
* Open top-up menu using the <u>“➕ Top Up Balance”</u> button.
* In the resulting menu, click on cryptocurrency name button.
* Copy cryptocurrency address, and send cryptocurrency on this address.
* Once your transaction has at least one confirmation you will receive notification from the bot.

<br>![img](https://i.imgur.com/j2l7fHc.gif)

---

### 2.3 Purchase of goods

To buy any item, go to "All categories" -> Select any category -> Select any subcategory -> Select quantity -> Confirm
purchase. If the purchase is successful, you will immediately receive a message in the format:

![img](https://i.imgur.com/yEUw32h.gif)

---

### 2.4 🧾 Purchase History

* To access your purchase history go to "My Profile" -> "Purchase History".
* You will be presented with an inline keyboard with all your purchases, by clicking on any of the purchases you will be
  sent a message in the format from paragraph 2.3.

![imb](https://i.imgur.com/t5sA38N.gif)

---

## 3.AiogramShopBot Admin Manual

---

### 3.1 Adding a new admin

To add a new admin you need to add his telegram id to the ADMIN_ID_LIST environment variable, separated by commas, and
reload the bot.<br>For example: ``ADMIN_ID_LIST=123456,654321``

---

### 3.2 📢 Announcements

---

### 3.2.1 📢 Send to Everyone

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the announcements menu using the <u>“📢 Announcements”</u> button.
* In the resulting menu, click on <u>“📢 Send to Everyone”</u> button.
* Type a message or forward to the bot, the bot supports sending a message with pictures and Telegram markup (bold,
  italics, spoilers, etc.).
* Confirm or decline the sending of messages.
* After successful message sending, the original message with inline buttons "Confirm", "Decline" will change like on
  gif.<br>

![img](https://i.imgur.com/JYN6qx0.gif)

---

### 3.2.2 🔄 Restocking Message

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the announcements menu using the <u>“📢 Announcements”</u> button.
* In the resulting menu, click on <u>“🔄 Restocking Message”</u> button.
* This message is generated based on items in the database that have "is_new" is true.

![img](https://i.imgur.com/lu3khwR.gif)

---

### 3.2.3 🗂️ Current Stock

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the announcements menu using the <u>“📢 Announcements”</u> button.
* In the resulting menu, click on <u>“🗂️ Current Stock”</u> button.
* This message is generated based on items in the database that have "is_sold" is false.

![img](https://i.imgur.com/T9wMPRG.gif)

---

### 3.3 📦 Inventory Management

---

#### 3.3.1 ➕ Add Items

---

##### 3.3.1.1 JSON

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the announcements menu using the <u>“📦 Inventory Management”</u> button.
* Open the add items menu using the <u>“➕ Add Items”</u> button.
* In the resulting menu, click on <u>“JSON”</u> button.
* Send .json file with new items.<br>Example of .json file:

> **⚠️ Note**<br>
> The "private_data" property is what the user gets when they make a purchase.

```
[
  {
    "item_type": "Physical",
    "category": "Category#1",
    "subcategory": "Subcategory#1",
    "price": 50,
    "description": "Mocked description",
    "private_data": null
  },
  {
    "item_type": "Digital",
    "category": "Category#2",
    "subcategory": "Subcategory#2",
    "price": 100,
    "description": "Mocked description",
    "private_data": "Mocked private data"
  }
]

```

![img](https://i.imgur.com/zjS4v8k.gif)

---

##### 3.3.1.2 TXT

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the inventory management menu using the <u>“📦 Inventory Management”</u> button.
* Open the add items menu using the <u>“➕ Add Items”</u> button.
* In the resulting menu, click on <u>“TXT”</u> button.
* Send .txt file with new items.<br>Example of .txt file:

```
PHYSICAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;null
PHYSICAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;null
PHYSICAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;null
PHYSICAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;null
DIGITAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;PRIVATE_DATA#5
DIGITAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;PRIVATE_DATA#6
DIGITAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;PRIVATE_DATA#7
DIGITAL;CATEGORY#1;SUBCATEGORY#1;DESCRIPTION#1;50.0;PRIVATE_DATA#8
```

![img](https://i.imgur.com/jct3qGc.gif)

---

#### 3.3.2 🗑️ Delete Category/Subcategory

> ⚠️ Note<br>
> This way, you will delete all products from “All categories” with the category or subcategory you picked and deleted.

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the inventory management menu using the <u>“📦 Inventory Management”</u> button.
* Open the add items menu using the <u>“🗑️ Delete Category”</u> or <u>“🗑️ Delete Subcategory”</u> button.
* In the resulting menu, select the category or subcategory you want to delete.
* Confirm or cancel the deletion of the category or subcategory.

![img](https://i.imgur.com/foFKU0y.gif)

---

### 3.4 👥 User Management

---

#### 3.4.1 💳 Credit Management

---

##### 3.4.1.1 ➕ Add balance

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the user management menu using the <u>“👥 User Management”</u> button.
* Open the credit management menu using the <u>“💳 Credit Management”</u> button.
* In the resulting menu, click on <u>“➕ Add balance”</u> button.
* Send the user entity object that belongs to the user you want to add the balance to. This can be telegram id or
  telegram username.
* Send the value by which you want to add the balance to the user.

![img](https://i.imgur.com/6HXd460.gif)

---

##### 3.4.1.2 ➖ Reduce balance

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the user management menu using the <u>“👥 User Management”</u> button.
* Open the credit management menu using the <u>“💳 Credit Management”</u> button.
* In the resulting menu, click on <u>“➖ Reduce balance”</u> button.
* Send the user entity object that belongs to the user you want to add the balance to. This can be telegram id or
  telegram username.
* Send the value by which you want to reduce the balance to the user.

![img](https://i.imgur.com/4JPbWZd.gif)

---

#### 3.4.2 ↩️ Make Refund

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the user management menu using the <u>“👥 User Management”</u> button.
* Open the refund menu using the <u>“↩️ Make Refund”</u> button.
* In the resulting menu, click on the buy button you want to refund.
* Confirm or cancel refund.

![img](https://i.imgur.com/hZ7UvJJ.gif)

---

### 3.5 📊 Analytics & Reports

---

### 3.5.1 📊 Statistics

* Open the admin menu using the <u>“🔑 Admin Menu”</u> button.
* Open the statistics menu using the <u>“📊 Analytics & Reports”</u> button.
* In the resulting menu, click on the entity for which you want to get statistics.
* In the resulting menu, click on the time period for which you want statistics.

![img](https://i.imgur.com/lmuo0QY.gif)

---

### 3.6 🔔 Admin notifications

> **⚠️ Note**<br>
> All users with telegram id in the .env ADMIN_ID_LIST environment variable will receive these notifications

---

#### 3.6.1 Notification to admin about new deposit

* If any user topped up the balance and clicked on the "Refresh balance" button, you will receive the following message
  from the bot:

![img](https://i.imgur.com/FSXzEoW.gif)

---

#### 3.6.2 Notification to admin about new buy

After each purchase, you will receive a message in the format:

![img](https://i.imgur.com/MeRkCYD.gif)

---

### 3.8 👛 Wallet

---

#### 3.8.1 Cryptocurrency withdrawal functionality

To withdraw cryptocurrency from the bot, open the admin menu, go to the wallet tab, select the cryptocurrency you want to withdraw, send the cryptocurrency address where you want to withdraw and confirm the withdrawal. After a successful withdrawal, the bot will send you a link to the blockchain browser with the transaction.

![img](https://i.imgur.com/gjkRFVb.gif)

---

### 3.9 📷 Media management

To change the media for a category, subcategory, or text buttons, open 🔑 Admin Menu->📷 Media management.
> **⚠️ Note**<br>
> Media can be GIFs, images, or videos.

![img](https://i.imgur.com/VIQdxvL.gif)

---

### 3.10 🎪 Coupons management

With 🎪 Coupons management, you can create a new coupon or modify an existing one.

---

#### 3.10.1 🎫 Create new coupon

To create a coupon, select the coupon type—either 📊 Percentage or 💰 Fixed. Then, choose the usage limit: ♾️ Infinite or 1️⃣ Single-use. Next, enter the coupon value (discount percentage or fixed amount). Provide a coupon name, and finally confirm or cancel the creation.

![img](https://i.imgur.com/1tfiFBw.gif)

---

#### 3.10.2 📋 View all coupons

You can disable or enable coupons. Open 🔑 Admin Menu->🎪 Coupons management->📋 View all coupons, select a coupon by name, and choose an action.

![img](https://i.imgur.com/dMZoOA3.gif)

---

### 3.11 📦 Shipping management

#### 3.11.1 🚚 Create new shipping option

To create a new shipping method, open 🔑 Admin Menu->📦 Shipping management->🚚 Create new shipping option, then enter the name of the shipping method and the cost in fiat currency.

![img](https://i.imgur.com/IqrdGL5.gif)

---

#### 3.11.2 📋 View all shipping options

You can change the price, name, or disable an existing shipping method. Open 🔑 Admin Menu->📦 Shipping management->📋 View all shipping options, then select the shipping method and choose the desired action.

![img](https://i.imgur.com/E2MHoaK.gif)

---

#### 3.12 🛍 Buys management

With 🛍 Buys management, you can view all your users' purchases. This feature is mainly used to update tracking numbers for physical goods purchases. After the tracking number is updated, the user will receive a notification.

![img](https://i.imgur.com/4aPUnHx.gif)

---

#### 3.13 ⭐ Reviews Management

With ⭐ Reviews Management, you can view all reviews of your customers' purchases. You can also delete the text and image of a review to avoid unwanted advertising.

![img](https://i.imgur.com/umBysXX.gif)

---

## 4.0 Cryptocurrency Forwarding 

You can enable cryptocurrency forwarding, in which case all cryptocurrency will be redirected from KryptoExpress addresses to your addresses.<br>
To enable cryptocurrency forwarding, you need to set the CRYPTO_FORWARDING_MODE variable to true and set values for {CRYPTO}_FORWARDING_ADDRESS in .env.
> **⚠️ Note**<br>
> BTC and LTC addresses must be in Bech32 format.

---

## 5.0 Referral System

The referral system is designed to stimulate organic growth of the bot while keeping the bonus economy fully controlled and predictable. All referral rewards are credited as internal bonus balance and cannot be withdrawn. Bonuses can only be used to purchase digital or physical products inside the bot.

---

### 5.1 Access to the Referral System

A user can become a referrer only after reaching a minimum total deposit amount.

- **MIN_REFERRER_TOTAL_DEPOSIT**  
  The minimum total amount of deposits required to unlock the referral system.

Until this threshold is reached, the user cannot generate or use a referral link.

---

### 5.2 How Referrals Work

Each eligible user can generate a unique referral link.  
When a new user joins the bot using this link and makes a deposit, the referral relationship is permanently established.

Referral bonuses are applied only to deposits made **after** the referral relationship is created.

---

### 5.3 Referral Bonuses (Referred User)

The referred user receives a bonus added to their balance on eligible deposits.

- **REFERRAL_BONUS_PERCENT**  
  Percentage bonus applied to each eligible deposit made by the referred user.

- **REFERRAL_BONUS_DEPOSIT_LIMIT**  
  Number of deposits that can receive the referral bonus.

- **REFERRAL_BONUS_CAP_PERCENT**  
  Maximum total bonus the referred user can receive, expressed as a percentage of their own deposits.

If the cap is reached, no further referral bonuses are granted.

---

### 5.4 Referrer Bonuses (Inviting User)

The referrer earns a bonus from the deposits made by each referred user.

- **REFERRER_BONUS_PERCENT**  
  Percentage of the referred user’s deposit credited to the referrer.

- **REFERRER_BONUS_DEPOSIT_LIMIT**  
  Number of deposits per referred user that generate a referrer bonus.

- **REFERRER_BONUS_CAP_PERCENT**  
  Maximum total bonus the referrer can earn from a single referred user, expressed as a percentage of that referral’s deposits.

---

### 5.5 Global Bonus Cap

To ensure economic safety, a global cap limits the total bonuses generated from a single referral.

- **TOTAL_BONUS_CAP_PERCENT**  
  The maximum combined bonus (referral + referrer) that can be generated from a referred user, expressed as a percentage of that user’s deposits.

If the combined bonuses exceed this limit, the system prioritizes the referred user’s bonus. Any remaining bonus capacity is applied to the referrer.

---

### 5.6 Anti-Abuse Guarantees

The referral system includes multiple safeguards:
- Referral access is locked behind a minimum deposit requirement
- Bonuses apply only to a limited number of deposits
- Individual and global bonus caps prevent excessive rewards
- Self-referrals are explicitly forbidden

These measures ensure sustainable growth and predictable costs without relying on product margins.

---


## 6.0 Admin panel with web interface (SQLAdmin)

You can work with database objects using the SQLAdmin admin panel.<br>
This panel is always available at {YOUR_IP_ADDRESS}.sslip.io/admin<br>
Login: admin<br>
Password: ${SQLADMIN_RAW_PASSWORD}

![img.png](https://i.imgur.com/s1EpxNR.png)

## 7.0 Multibot (Experimental functionality)

### 7.1 Starting the multibot

* Set all environment variables in docker-compose.yml and set the variable “true” for MULTIBOT.
  ``MULTIBOT="true"``
* Run the ``docker-compose up`` command.
* After successful execution of the command, you will only deploy a manager bot for other bots, it will not have
  functionality for buying items etc. To deploy a bot with functionality to sell goods etc..., you need to send the
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
- [x] Make the functionality of generating statistics of deposits in the bot for a month/week in the admin
  panel.
- [x] Functionality for sorting products by name/quantity/price.
- [x] Functionality for searching products by name (filtering).
- [x] Cryptocurrency forwarding mode.
- [x]  Functionality for adding media to categories/subcategories/buttons. Media can be GIFs, images, or videos.
- [x]  Improved shopping cart functionality, added the ability to add and remove products as in marketplaces (+1/-1 buttons).
- [x]  Improved User Management functionality, added user blocking functionality.
- [x]  Review functionality.
- [x]  Functionality for selling physical goods with shipping.
- [x]  Multiple localization (i18n), the bot will respond in the language of your Telegram application or in English by default.
- [x]  Referral system.
- [x]  Web interface for the admin panel. (SQLAdmin)
- [x]  Interactive script for deploying the bot without programming skills, etc.

