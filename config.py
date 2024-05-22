import asyncio
import asyncpg
# PERMANENT_MAILING_TASK_INTERVAL_MINS = 0.1
# PERMANENT_TARIFF_UPDATE_TASK_MINS = 1
# DEFAULT_ADMIN_MAILING_INTERVAL_HOURS = 24
# MIN_SEARCH_SIMILARITY = 0.1
# #TRANSMIT_BY_INHERITANCE_TARIFFS = ["premium", "vip"]
# TRANSMIT_BY_INHERITANCE_TARIFFS = "premium,vip"
# MIN_WITHDRAWAL_AMOUNT = 100.0
# MAX_PHOTO_SIZE = 500000

# schedule_local_config = {
#     "permanent_mailing_task_interval_mins": 0.1,
#     "permanent_tariff_update_task_mins": 10
# }

connection_params = {
    "user": "postgres",
    "password": "1234",
    "database": "bot_database",
    "host": "psql_cont",
    "port": 5432,
}

# async def set_local_tasks_params():
#     conn = await asyncpg.connect(**connection_params)
#     schedule_config_row = await conn.fetchrow("SELECT permanent_mailing_task_interval_mins, permanent_tariff_update_task_mins FROM config LIMIT 1")
#     schedule_local_config = schedule_config_row
#     await conn.close()

# asyncio.run(set_local_tasks_params())