import os
import shutil
from datetime import datetime
import pickle
import json
import boto3
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram import Bot


ROOT_DIR = os.getenv("ROOT_DIR")

def old_make_product_media_dir(folder_name: str) -> str:
    path = old_get_products_dir_path + folder_name
    if os.path.exists(path) == False:
        os.makedirs(path)
    return path

async def add_catalog_media_file(photo, catalog_id: int, bot: Bot):
    bin_photo=None
    bin_photo = await bot.download(file=photo)
    destination = "catalogs/" + str(catalog_id) + ".jpg"
    s3.Bucket(os.getenv("BUCKET_NAME")).put_object(Key=destination, Body=bin_photo)

async def add_product_media_file(photo, product_id: int, photo_num: int, bot: Bot):
    bin_photo=None
    bin_photo = await bot.download(file=photo)
    destination = str(product_id) + "/" + str(photo_num) + ".jpg"
    s3.Bucket(os.getenv("BUCKET_NAME")).put_object(Key=destination, Body=bin_photo)

async def old_add_catalog_media_file(photo, catalog_id: int, bot: Bot):
    destination=old_get_catalogs_dir_path() + str(catalog_id) + ".jpg"
    await bot.download(file=photo,
                    destination=destination)
    
async def old_add_product_media_file(photo, dir_path: str, photo_num: int, bot: Bot):
    destination=dir_path + "/" + str(photo_num) + ".jpg"
    await bot.download(file=photo,
                    destination=destination)
    
def get_catalog_album_builder(catalog_id: int) -> MediaGroupBuilder:
    album_builder = MediaGroupBuilder()
    for photo_obj in s3.Bucket(os.getenv("BUCKET_NAME")).objects.filter(Prefix="catalogs/" + str(catalog_id)):
        photo = photo_obj.get()
        album_builder.add_photo(media=BufferedInputFile(file=photo["Body"].read(), filename=str(catalog_id)))
    return album_builder

def old_get_catalog_album_builder(catalog_id: int) -> MediaGroupBuilder:
    album_builder = MediaGroupBuilder()
    dir_path = old_get_catalogs_dir_path()
    album_builder.add_photo(media=FSInputFile(dir_path + str(catalog_id)))
    return album_builder

def get_product_album_builder(product_id: int) -> MediaGroupBuilder:
    album_builder = MediaGroupBuilder()
    for photo_obj in s3.Bucket(os.getenv("BUCKET_NAME")).objects.filter(Prefix=str(product_id)+"/"):
        photo = photo_obj.get()
        album_builder.add_photo(media=BufferedInputFile(file=photo["Body"].read(), filename=str(product_id)))
    return album_builder

def old_get_product_album_builder(product_id: int) -> MediaGroupBuilder:
    album_builder = MediaGroupBuilder()
    dir_path = old_get_products_dir_path() + str(product_id)
    for photo_file_name in os.listdir(dir_path):
        album_builder.add_photo(media=FSInputFile(dir_path + "/" + photo_file_name))
    return album_builder

def old_get_products_dir_path() -> str:
    path = ROOT_DIR + "/Files/Products/" 
    return path

def old_get_catalogs_dir_path() -> str:
    path = ROOT_DIR + "/Files/Catalogs/" 
    return path

def get_product_objects(product_id: int) -> list:
    return s3.Bucket(os.getenv("BUCKET_NAME")).objects.filter(Prefix=str(product_id)+"/")

def old_get_product_objects(product_id: int) -> list:
    dir_path = old_get_products_dir_path() + str(product_id)
    return os.listdir(dir_path)

def remove_product_media_dir(folder_name: str):
    for photo_obj in s3.Bucket(os.getenv("BUCKET_NAME")).objects.filter(Prefix=folder_name+"/"):
        photo_obj.delete()

def old_remove_product_media_dir(folder_name: str):
    path = old_get_products_dir_path + folder_name
    if os.path.exists(path) == True:
        shutil.rmtree(path) #filing

def remove_catalog_media(catalog_id: int):
    for photo_obj in s3.Bucket(os.getenv("BUCKET_NAME")).objects.filter(Prefix="catalogs/" + str(catalog_id)):
        photo_obj.delete()

def delete_obj(obj_key: str):
    s3.Bucket(os.getenv("BUCKET_NAME")).Object(obj_key).delete()

def delete_product_photo(product_id: int, photo_file_name: str):
    dir_path = old_get_products_dir_path() + str(product_id)
    os.remove(dir_path+"/"+photo_file_name)

def old_remove_catalog_media(catalog_id: int):
    path = old_get_catalogs_dir_path + str(catalog_id)
    if os.path.exists(path) == True:
        os.remove(path)

def get_last_tariff_check_date() -> datetime:
    path = ROOT_DIR + "/Files/last_tariff_check_date.pickle"
    with open(path, "rb") as file:
        return pickle.load(file)
    
def set_last_tariff_check_date(last_check_date: datetime):
    path = ROOT_DIR + "/Files/last_tariff_check_date.pickle"
    with open(path, "wb") as file:
        pickle.dump(last_check_date, file)

languages: dict = {}
with open(ROOT_DIR + "/languages.json", "r") as file:
    languages = json.load(file)


# with open(file="~/.aws/credentials", mode="w") as file:
#     file.write("[default]")
#     file.write(f"aws_access_key_id = {os.getenv('AWS_ACCESS_KEY_ID')}")
#     file.write(f"aws_secret_access_key = {os.getenv('AWS_SECRET_ACCESS_KEY')}")
    
    
#session = boto3.session.Sessions()
#session = boto3.Session(aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'))
session = boto3.Session(aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'))
s3 = boto3.resource("s3", endpoint_url = "https://storage.yandexcloud.net")


