"""
This example shows how to use webhook on behind of any reverse proxy (nginx, traefik, ingress etc.)
"""
import logging
import sys
from dotenv.main import load_dotenv
import os

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage #!

from Routers.common_router import common_router
from Routers.auth_router import auth_router
from Routers.error_router import error_router
from Routers.manage_catalog_router import manage_catalog_router
from Routers.manage_product_router import manage_product_router
from Routers.view_router import view_router
from Routers.tariff_router import tariff_router
from Routers.admin_router import admin_router
from Routers.user_router import user_router
from Routers.support_router import support_router
from Routers.buy_router import buy_router
from Routers.search_router import search_router
from Routers.withdrawal_router import withdrawal_router
from Routers.special_router import special_router

from Middlewares.outer_middlewares import UserInfoAndBotBlockingMiddleware
from Middlewares.middlewares import DeleteWaitingCbckMessageMiddleware, lang_code_middleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Utils.Methods.mailing import permanent_mailing_task
from Utils.Methods.tariff_upd import permanent_tariff_update_task
from Sources.files import set_last_tariff_check_date

from datetime import datetime

import asyncio

from Files import buffer


load_dotenv()
# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.environ['BOT_TOKEN']

# Webserver settings
# bind localhost only to prevent any external access
WEB_SERVER_HOST = os.environ["WEB_SERVER_HOST"]
# Port for incoming request from reverse proxy. Should be any available port
WEB_SERVER_PORT = int(os.environ["WEB_SERVER_PORT"])

# Path to webhook route, on which Telegram will send requests
WEBHOOK_PATH = "/webhook"
# Secret key to validate requests from Telegram (optional)
WEBHOOK_SECRET = "1234"
# Base URL for webhook will be used to generate webhook URL for Telegram,
# in this example it is used public DNS with HTTPS support
BASE_WEBHOOK_URL = os.environ['WEBHOOK_URL']



async def on_startup(bot: Bot) -> None:
    # If you have a self-signed SSL certificate, then you will need to send a public
    # certificate to Telegram
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)


def main() -> None:
    # Dispatcher is a root router
    dp = Dispatcher(storage=MemoryStorage())
    # ... and all other routers should be attached to Dispatcher
    #dp.pre_checkout_query.register(pre_checkout_query)

    dp.include_routers(special_router, withdrawal_router, search_router, buy_router, admin_router, support_router, user_router, manage_catalog_router, common_router, manage_product_router, view_router, tariff_router, auth_router, error_router)

    #dp.update.outer_middleware(BotBlockingMiddleware())
    dp.update.outer_middleware(UserInfoAndBotBlockingMiddleware())
    dp.update.middleware(DeleteWaitingCbckMessageMiddleware())
    dp.update.middleware(lang_code_middleware())
    # Register startup hook to initialize webhook
    dp.startup.register(on_startup)

    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)

    # task = asyncio.create_task(test_start_mailing(bot))
    # print("after_task")

    # asyncio.run(t_s_m(bot))
    # print("after_t_s_m")

    # Create aiohttp.web.Application instance
    app = web.Application()

    # Create an instance of request handler,
    # aiogram has few implementations for different cases of usage
    # In this example we use SimpleRequestHandler which is designed to handle simple cases
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    )
    # Register webhook handler on application
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dp, bot=bot)

    # And finally start webserver
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    print(BASE_WEBHOOK_URL)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    #asyncio.run(main())
    main()

