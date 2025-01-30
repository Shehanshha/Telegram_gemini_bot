from pymongo import MongoClient
from datetime import datetime
from config import Config
import logging

logger = logging.getLogger(__name__)

client = MongoClient(Config.MONGODB_URI)
db = client.telegram_bot

class Database:
    @staticmethod
    def get_user(chat_id):
        try:
            return db.users.find_one({"chat_id": chat_id})
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None

    @staticmethod
    def create_user(user_data):
        try:
            return db.users.insert_one(user_data)
        except Exception as e:
            logger.error(f"Create user error: {e}")

    @staticmethod
    def update_phone(chat_id, phone):
        try:
            return db.users.update_one(
                {"chat_id": chat_id},
                {"$set": {"phone": phone, "verified": True}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Update phone error: {e}")

    @staticmethod
    def save_message(chat_id, user_message, bot_response):
        try:
            return db.messages.insert_one({
                "chat_id": chat_id,
                "user_message": user_message,
                "bot_response": bot_response,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Save message error: {e}")

    @staticmethod
    def save_image(chat_id, file_id, description):
        try:
            return db.images.insert_one({
                "chat_id": chat_id,
                "file_id": file_id,
                "description": description,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Save image error: {e}")

    @staticmethod
    def get_chat_history(chat_id, limit=10):
        try:
            return list(db.messages.find(
                {"chat_id": chat_id},
                {"_id": 0, "user_message": 1, "bot_response": 1, "timestamp": 1}
            ).sort("timestamp", -1).limit(limit))
        except Exception as e:
            logger.error(f"Chat history error: {e}")
            return []