from Sources.db import connection_params
import asyncpg
import asyncio
from dotenv.main import load_dotenv
import os
import json

load_dotenv()

async def create_db_tables():
    conn = await asyncpg.connect(**connection_params)

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                tg_user_id BIGINT, 
                role VARCHAR(50),
                bonuses REAL,
                login VARCHAR(255),
                referer_id INT REFERENCES accounts(id),
                ref_link VARCHAR(255),
                language_code VARCHAR(50),
                blocking VARCHAR(50),
                source VARCHAR(50),
                show_award_notifications BOOLEAN
        )
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS catalogs (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                owner_id INT REFERENCES accounts(id),
                status VARCHAR(50)
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                parent_cat_id INT REFERENCES categories(id)
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                catalog_id INT REFERENCES catalogs(id),
                description TEXT, 
                category_id INT REFERENCES categories(id)
        )  
    ''')

    # await conn.execute('''
    #     CREATE TABLE IF NOT EXISTS photos (
    #             id SERIAL PRIMARY KEY,
    #             file_path VARCHAR(255), 
    #             product_id INT REFERENCES products(id)
    #     )  
    # ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS mailing_buffer (
                id SERIAL PRIMARY KEY,
                catalog_id INT REFERENCES catalogs(id),
                next_mailing_date timestamp, 
                mailing_interval interval
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS moderation_list (
                id SERIAL PRIMARY KEY,
                catalog_id INT REFERENCES catalogs(id),
                moderator_id INT REFERENCES accounts(id),
                moderation_date timestamp, 
                status VARCHAR(50)
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS tariff_params (
                tariff VARCHAR(50) PRIMARY KEY,
                max_own_catalog_count INT,
                max_own_product_count INT,  
                mailing_line_count INT,
                mailing_off_lines_count INT,
                admin_mailing_catalog_count INT,
                mailing_interval interval, 
                price_p_m INT, 
                price_p_y INT
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS tariff_buffer (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES accounts(id),
                is_active BOOLEAN,
                tariff VARCHAR(50) REFERENCES tariff_params(tariff),
                remains interval
        )  
    ''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS waiting_cbck_buffer (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT,
                message_id BIGINT
        )  
    ''')

    # await conn.execute('''
    #     CREATE TABLE IF NOT EXISTS violation_list (
    #             id SERIAL PRIMARY KEY,
    #             user_id INT REFERENCES accounts(id),
    #             catalog_id INT REFERENCES catalogs(id)
    #     )  
    # ''')

    await conn.execute('''CREATE TABLE withdrawal_list (id SERIAL PRIMARY KEY, user_id int REFERENCES accounts(id), bank_card_number VARCHAR(50), amount REAL, moderator_id INT REFERENCES accounts(id), moderation_date timestamp, status VARCHAR(50))''')

    await conn.execute('''
        CREATE TABLE IF NOT EXISTS config (
                PERMANENT_MAILING_TASK_INTERVAL_MINS real, 
                PERMANENT_TARIFF_UPDATE_TASK_MINS int, 
                DEFAULT_ADMIN_MAILING_INTERVAL_HOURS int,
                MIN_SEARCH_SIMILARITY real, 
                TRANSMIT_BY_INHERITANCE_TARIFFS VARCHAR(50),
                MIN_WITHDRAWAL_AMOUNT real, 
                MAX_PHOTO_SIZE int
        )
    ''')

    await conn.close()

async def fill_config_table():
    conn = await asyncpg.connect(**connection_params)
    # await conn.execute('''UPDATE config SET
    #     PERMANENT_MAILING_TASK_INTERVAL_MINS = 0.1, 
    #     PERMANENT_TARIFF_UPDATE_TASK_MINS 1, 
    #     DEFAULT_ADMIN_MAILING_INTERVAL_HOURS 24,
    #     MIN_SEARCH_SIMILARITY 0.1, 
    #     TRANSMIT_BY_INHERITANCE_TARIFFS VARCHAR(50) = 'premium,vip',
    #     MIN_WITHDRAWAL_AMOUNT = 100.0, 
    #     MAX_PHOTO_SIZE = 500000
    # ''')

    await conn.execute('''
        INSERT INTO config (PERMANENT_MAILING_TASK_INTERVAL_MINS, PERMANENT_TARIFF_UPDATE_TASK_MINS, DEFAULT_ADMIN_MAILING_INTERVAL_HOURS,
                    MIN_SEARCH_SIMILARITY,  TRANSMIT_BY_INHERITANCE_TARIFFS,  MIN_WITHDRAWAL_AMOUNT, MAX_PHOTO_SIZE ) VALUES 
                       (0.1, 1, 24, 0.1, 'premium,vip', 100.0, 500000)
    ''')

    await conn.close()


async def fill_tariff_params_table():
    conn = await asyncpg.connect(**connection_params)

    await conn.execute('''UPDATE tariff_params SET 
        max_own_catalog_count = 1,
        max_own_product_count = 1,
        mailing_line_count = 1,
        mailing_interval = '14 days',
        price_p_m = NULL,
        price_p_y = NULL,
        admin_mailing_catalog_count = NULL,
        mailing_off_lines_count = 0 
            WHERE tariff = 'base'
    ''')
    await conn.execute('''UPDATE tariff_params SET 
        max_own_catalog_count = 1,
        max_own_product_count = 5,
        mailing_line_count = 3,
        mailing_interval = '7 days',
        price_p_m = 200,
        price_p_y = 2000,
        admin_mailing_catalog_count = NULL,
        mailing_off_lines_count = 3 
            WHERE tariff = 'advanced'
    ''')
    await conn.execute('''UPDATE tariff_params SET 
        max_own_catalog_count = 2,
        max_own_product_count = 20,
        mailing_line_count = 5,
        mailing_interval = '2 days 07:12:00',
        price_p_m = 500,
        price_p_y = 5000,
        admin_mailing_catalog_count = 3,
        mailing_off_lines_count = 5 
            WHERE tariff = 'business'
    ''')
    await conn.execute('''UPDATE tariff_params SET 
        max_own_catalog_count = 3,
        max_own_product_count = 100,
        mailing_line_count = 20,
        mailing_interval = '1 day 09:36:00',
        price_p_m = 2000,
        price_p_y = 20000,
        admin_mailing_catalog_count = 1,
        mailing_off_lines_count = 20 
            WHERE tariff = 'premium'
    ''')
    await conn.execute('''UPDATE tariff_params SET 
        max_own_catalog_count = 5,
        max_own_product_count = 500,
        mailing_line_count = NULL,
        mailing_interval = '1 day',
        price_p_m = 5000,
        price_p_y = 50000,
        admin_mailing_catalog_count = 0,
        mailing_off_lines_count = NULL 
            WHERE tariff = 'vip'
    ''')
    
    await conn.close()


async def create_idx_trgm_description():
    conn = await asyncpg.connect(**connection_params)
    
    conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
    conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    conn.execute("CREATE INDEX idx_trgm_description ON products USING gin(description gin_trgm_ops)")

    await conn.close()


async def fill_categories_table():
    conn = await asyncpg.connect(**connection_params)
    pass
    await conn.close()


if __name__ == "__main__":
    asyncio.run(create_db_tables())
