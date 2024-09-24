from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

db_username = os.getenv('DB_USER_NAME')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')


def get_mongodb_connection_string():
    return f"mongodb+srv://{db_username}:{db_password}@cluster0.mjgbz1t.mongodb.net/{db_name}"


client = AsyncIOMotorClient(get_mongodb_connection_string())
db = client[db_name]