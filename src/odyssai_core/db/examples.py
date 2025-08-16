"""
Example usage of MongoDB connection for OdyssAI Core
"""

import logging
from db import get_database, MongoDBClient
from db.connection import test_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_connection():
    """Example of basic MongoDB connection"""
    try:
        # Test connection
        if test_connection():
            print("✅ MongoDB connection successful!")
            
            # Get database
            db = get_database("odyssai")
            
            # List collections
            collections = db.list_collection_names()
            print(f"📂 Collections in database: {collections}")
            
        else:
            print("❌ MongoDB connection failed!")
            
    except Exception as e:
        logger.error(f"Error in basic connection example: {e}")


def example_client_operations():
    """Example of using MongoDBClient for operations"""
    try:
        # Initialize client
        mongo_client = MongoDBClient("odyssai")
        
        # Example: Insert a document
        test_doc = {
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2025-08-16"
        }
        
        doc_id = mongo_client.insert_one("users", test_doc)
        if doc_id:
            print(f"✅ Document inserted with ID: {doc_id}")
            
            # Example: Validate ObjectId
            if mongo_client.is_valid_object_id(doc_id):
                print(f"✅ '{doc_id}' is a valid ObjectId")
                
                # Example: Find by ID (using ObjectId)
                found_doc = mongo_client.find_by_id("users", doc_id)
                if found_doc:
                    print(f"📄 Found document by ID: {found_doc}")
                    
                    # Example: Update by ID (using ObjectId)
                    updated = mongo_client.update_by_id(
                        "users", 
                        doc_id, 
                        {"updated_at": "2025-08-16", "status": "active"}
                    )
                    if updated:
                        print("✅ Document updated by ID successfully")
                    
                    # Example: Generate new ObjectId
                    new_id = mongo_client.generate_object_id()
                    print(f"🆕 Generated new ObjectId: {new_id}")
                    
                    # Example: Count documents
                    count = mongo_client.count_documents("users")
                    print(f"📊 Total users: {count}")
                    
                    # Example: Delete by ID (using ObjectId)
                    deleted = mongo_client.delete_by_id("users", doc_id)
                    if deleted:
                        print("🗑️ Document deleted by ID successfully")
        
        # Example: Invalid ObjectId handling
        invalid_id = "invalid_id_123"
        if not mongo_client.is_valid_object_id(invalid_id):
            print(f"❌ '{invalid_id}' is not a valid ObjectId")
        
    except Exception as e:
        logger.error(f"Error in client operations example: {e}")


if __name__ == "__main__":
    print("🚀 OdyssAI MongoDB Examples")
    print("=" * 40)
    
    print("\n1. Testing basic connection...")
    example_basic_connection()
    
    print("\n2. Testing client operations...")
    example_client_operations()
    
    print("\n✨ Examples completed!")
