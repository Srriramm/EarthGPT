"""MongoDB database connection and configuration."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from config import settings
from loguru import logger
import asyncio
from typing import Optional


class MongoDB:
    """MongoDB database connection manager."""
    
    def __init__(self):
        self.client: Optional["AsyncIOMotorClient"] = None
        self.database: Optional["AsyncIOMotorDatabase"] = None
    
    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.database = self.client[settings.mongodb_database]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
            
            # Create indexes
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client is not None:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for better performance."""
        try:
            # Users collection indexes
            users_collection = self.database.users
            await users_collection.create_index("email", unique=True)
            await users_collection.create_index("username", unique=True)
            
            # Chat sessions collection indexes
            sessions_collection = self.database.chat_sessions
            await sessions_collection.create_index([("user_id", 1), ("created_at", -1)])
            await sessions_collection.create_index("session_id", unique=True)
            
            # Messages collection indexes
            messages_collection = self.database.chat_messages
            await messages_collection.create_index([("user_id", 1), ("session_id", 1), ("timestamp", -1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")


# Global database instance
mongodb = MongoDB()


async def get_database() -> Optional["AsyncIOMotorDatabase"]:
    """Get database instance."""
    if mongodb.database is None:
        await mongodb.connect()
    return mongodb.database

