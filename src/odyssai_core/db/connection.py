"""
MongoDB Atlas connection module
Handles database connection and client management
"""

import logging
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from typing import Optional

from .config import MONGODB_URI

# Configure logging
logger = logging.getLogger(__name__)

# Global client instance
_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_client() -> MongoClient:
    """
    Get MongoDB client instance (singleton pattern)
    
    Returns:
        MongoClient: The MongoDB client instance
        
    Raises:
        ConnectionFailure: If unable to connect to MongoDB
    """
    global _client
    
    if _client is None:
        try:
            _client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,         # 10 second connection timeout
                socketTimeoutMS=20000,          # 20 second socket timeout
                maxPoolSize=50,                 # Maximum connection pool size
                retryWrites=True                # Enable retry writes
            )
            # Test the connection
            _client.admin.command('ping')
            logger.info("Successfully connected to MongoDB Atlas")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise
    
    return _client


def get_database(database_name: str = "odyssai") -> Database:
    """
    Get database instance
    
    Args:
        database_name (str): Name of the database (default: "odyssai")
        
    Returns:
        Database: The MongoDB database instance
    """
    global _database
    
    client = get_client()
    _database = client[database_name]
    
    return _database


def close_connection():
    """
    Close MongoDB connection
    """
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def test_connection() -> bool:
    """
    Test MongoDB connection
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_client()
        # Ping the database
        client.admin.command('ping')
        logger.info("MongoDB connection test successful")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {e}")
        return False
