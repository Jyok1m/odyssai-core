#!/usr/bin/env python3
"""
Test script for user creation to verify the enum serialization fix
"""

import sys
import os
import datetime
from uuid import uuid4

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from odyssai_core.db import MongoDBClient
from odyssai_core.db.schemas import UserSchema
from bcrypt import hashpw, gensalt

def test_user_creation():
    """Test user creation with enum handling"""
    print("Testing user creation...")
    
    client = MongoDBClient(validate_schemas=True)
    
    # Create a test user
    hashed_password = hashpw("testpassword123".encode(), gensalt()).decode()
    new_uuid = str(uuid4())
    
    user = UserSchema(
        username="test_user_" + new_uuid[:8],
        password=hashed_password,
        uuid=new_uuid,
        created_at=datetime.datetime.utcnow(),
    )
    
    print(f"Created user schema: {user.username}")
    print(f"User UUID: {user.uuid}")
    
    # Convert to dict
    user_dict = user.to_dict()
    print(f"User dict role: {user_dict['role']} (type: {type(user_dict['role'])})")
    
    try:
        # Insert user
        user_id = client.insert_one("users", user_dict)
        
        if user_id:
            print(f"✅ User created successfully! MongoDB ID: {user_id}")
            
            # Verify the user was created
            found_user = client.find_one("users", {"uuid": new_uuid})
            if found_user:
                print(f"✅ User found in database: {found_user['username']}")
                print(f"✅ Role in database: {found_user['role']} (type: {type(found_user['role'])})")
                
                # Clean up - delete the test user
                deleted = client.delete_one("users", {"uuid": new_uuid})
                if deleted:
                    print("✅ Test user cleaned up successfully")
                else:
                    print("⚠️ Failed to clean up test user")
            else:
                print("❌ User not found in database after creation")
        else:
            print("❌ Failed to create user")
            
    except Exception as e:
        print(f"❌ Error during user creation: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_creation()
