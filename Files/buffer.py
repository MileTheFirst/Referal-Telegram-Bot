from apscheduler.schedulers.asyncio import AsyncIOScheduler
# {
#     "permanent_mailing_job": null,
#     "permanent_tariff_update_job": null
# }

# permanent_mailing_job = None
# permanent_tariff_update_job = None
scheduler = AsyncIOScheduler()

bot_blocked = False
