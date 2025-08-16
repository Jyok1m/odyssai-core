"""
Database module for OdyssAI Core
Handles MongoDB Atlas connection and operations
"""

from .connection import get_database, get_client
from .client import MongoDBClient

__all__ = ["get_database", "get_client", "MongoDBClient"]
