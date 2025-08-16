"""
Database configuration for OdyssAI Core
"""

import os
from typing import Optional

def get_mongodb_uri(database: Optional[str] = None) -> str:
    """
    Get MongoDB Atlas connection string
    
    Args:
        database (Optional[str]): Specific database name to append to URI
        
    Returns:
        str: MongoDB connection URI
    """

    # Base URI
    uri = os.getenv("MONGODB_URI", "")
    
    # Add database if specified
    if database:
        uri += database
    
    return uri

# Default connection URI
MONGODB_URI = get_mongodb_uri()
