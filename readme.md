<h1 align="center">AiogramShopBot</h1>

<p align="center">
  <strong>🛍️ Production-style Telegram shop bot with crypto payments, admin flows, FastAPI webhooks, and multibot support.</strong>
</p>

<p align="center">
  <a href="https://t.me/demo_aiogramshopbot">
    <img src="https://img.shields.io/badge/Live_Demo_Bot-blue?logo=probot&logoColor=white" alt="Live bot"/>
  </a>
  <a href="https://t.me/ilyarolf_dev">
    <img src="https://img.shields.io/badge/Contact_me-blue?logo=telegram&logoColor=white" alt="Business offer"/>
  </a>
</p>

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?logo=python&logoColor=%23fff)](https://www.python.org/downloads/release/python-3127/)
[![Dockerhub](https://img.shields.io/badge/Docker_Hub-2496ED?logo=docker&logoColor=fff)](https://hub.docker.com/r/ilyarolf/aiogram-shop-bot)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)](https://www.sqlite.org/)
[![Bitcoin](https://img.shields.io/badge/Bitcoin-FF9900?logo=bitcoin&logoColor=white)](https://github.com/bitcoin/bitcoin)
[![Dogecoin](https://img.shields.io/badge/Dogecoin-C2A633?logo=dogecoin&logoColor=white)](https://dogecoin.com/)
[![Litecoin](https://img.shields.io/badge/Litecoin-A6A9AA?logo=litecoin&logoColor=white)](https://github.com/litecoin-project/litecoin)
[![Solana](https://img.shields.io/badge/Solana-9945FF?logo=solana&logoColor=fff)](https://github.com/solana-labs/solana)
[![Ethereum](https://img.shields.io/badge/Ethereum-3C3C3D?logo=ethereum&logoColor=white)](https://github.com/ethereum)
[![BinanceCoin](https://img.shields.io/badge/Binance-FCD535?logo=binance&logoColor=000)](https://github.com/binance)
[![Tether](https://img.shields.io/badge/Tether-168363?&logo=tether&logoColor=white)](https://tether.to/)
[![USD Coin](https://img.shields.io/badge/USD%20Coin-2775CA?&logo=usd-coin&logoColor=white)](https://www.usdc.com/)

**AiogramShopBot** is an open source Telegram shop bot built with **Aiogram 3**, **FastAPI**, **SQLAlchemy async**, **PostgreSQL**, **Redis**, **Docker Compose**, and **SQLAdmin**. It helps you sell **digital goods** and **physical goods** inside Telegram with built-in **cryptocurrency payments**, **shopping cart**, **purchase history**, **admin tools**, **shipping**, **reviews**, **coupons**, **analytics**, **referrals**, and **multi-language support**.

This repository is designed for developers and product teams who need a production-style Telegram ecommerce bot with a web admin panel, payment processing, localization, and scalable deployment.

## ✨ Why This Project

- Sell digital and physical products directly in Telegram.
- Accept crypto top-ups with Bitcoin, Dogecoin, Litecoin, Solana, Ethereum, Binance Coin, USDT, and USDC networks.
- Manage inventory, users, coupons, shipping, reviews, media, and purchases from Telegram admin flows.
- Use PostgreSQL, Redis, webhook mode, and Docker-based deployment for production setups.
- Extend the project with FastAPI routes, SQLAdmin, repositories, services, and Aiogram handlers.

## 🚀 Core Features

- Telegram storefront with categories, subcategories, cart, checkout, and purchase history.
- Admin menu for announcements, inventory, user management, analytics, wallet operations, media, coupons, shipping, buys, and reviews.
- Crypto payment integration with KryptoExpress.
- Referral system with limits and anti-abuse rules.
- Localization through JSON translation files.
- SQLAdmin web panel for database objects.
- Docker Compose setup for local and production-like environments.
- Multibot mode with one main bot and managed child bots.

## 🧰 Tech Stack

- Python 3.12
- Aiogram 3
- FastAPI
- SQLAlchemy async
- PostgreSQL
- Redis
- Alembic
- SQLAdmin
- Docker Compose

## ⚡ Quick Start

### 🖥️ Interactive deployment

Run the installer script on your VPS:

```bash
sudo sh -c "$(curl -fsSL https://raw.githubusercontent.com/ilyarolf/AiogramShopBot/refs/heads/master/scripts/deploy.sh)"
```

### 💻 Local development

```bash
git clone https://github.com/ilyarolf/AiogramShopBot.git
cd AiogramShopBot
pip install -r requirements.txt
python run.py
```

You will also need PostgreSQL, Redis, environment variables, and webhook/reverse proxy configuration.

Full setup guide:
- [Deployment and environment variables](docs.md#deployment-and-configuration)
- [Local run example](docs.md#local-development-example)

## 🎬 Product Walkthrough

### 💳 User balance top-up

![Top Up Balance Demo](https://i.imgur.com/j2l7fHc.gif)

### 🛒 Product purchase flow

![Purchase Flow Demo](https://i.imgur.com/yEUw32h.gif)

### 🧾 Purchase history

![Purchase History Demo](https://i.imgur.com/t5sA38N.gif)

### 👛 Admin wallet withdrawal

![Wallet Demo](https://i.imgur.com/gjkRFVb.gif)

More Telegram bot GIF demos, admin flow examples, and screenshots are available in [docs.md](docs.md#demo-gallery).

## 📚 Documentation

- [Full documentation](docs.md)
- [Deployment and configuration](docs.md#deployment-and-configuration)
- [User manual](docs.md#user-manual)
- [Admin manual](docs.md#admin-manual)
- [Referral system](docs.md#referral-system)
- [Cryptocurrency forwarding](docs.md#cryptocurrency-forwarding)
- [SQLAdmin panel](docs.md#sqladmin-web-admin-panel)
- [Multibot mode](docs.md#multibot-experimental)

## 🎯 Use Cases

- Telegram shop bot for digital products
- Telegram bot for physical goods with shipping
- Crypto-funded Telegram marketplace
- Telegram multibot commerce setup with one manager bot
- Aiogram ecommerce starter project
- FastAPI + Aiogram + SQLAlchemy production template
- Telegram admin panel and back office automation

## 🤝 Commercial Contact

- Demo bot: [@demo_aiogramshopbot](https://t.me/demo_aiogramshopbot)
- Commercial requests: [@ilyarolf_dev](https://t.me/ilyarolf_dev)

## 💖 Donate

- BTC: `bc1q2kv89q8yvf068xxw3x65gzfag98l9wnrda3x56`
- DOGE: `D8BFXqDM7MHf3A4j3kC8wWEN8DqRLVQjax`
- LTC: `ltc1q0tuvm5vqn9le5zmhvhtp7z9p2eu6yvv24ey686`
- SOL: `Avm7VAqPrwpHteXKfDTRFjpj6swEzjmj3a2KQvVDvugK`
- ETH: `0xB49D720DE2630fA4C813d5B4c025706E25cF74fe`
- TON: `UQD0QetwXoYTsmbZWVbE_z_JUFh54RVVRUxCbCHQkLsl3Hfn`
- USDT ERC20: `0xB49D720DE2630fA4C813d5B4c025706E25cF74fe`
- USDT BEP20: `0xB49D720DE2630fA4C813d5B4c025706E25cF74fe`

## 📄 License

[MIT License](LICENSE)
