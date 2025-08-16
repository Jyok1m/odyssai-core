from flask import Blueprint, jsonify, request
from typing import Dict, Optional
from odyssai_core.db import MongoDBClient
from odyssai_core.db.schemas import UserSchema, InteractionSchema
from odyssai_core.modules.validators import check_empty_fields
from bcrypt import hashpw, checkpw, gensalt
from uuid import uuid4
import datetime

# Create the system blueprint
users_bp = Blueprint("users", __name__)
client = MongoDBClient(validate_schemas=True)


@users_bp.route("/health", methods=["GET"])
def health_check():
    """Health check verification for the user API endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "odyssai-core",
            "version": "1.0.0",
        }
    ), 200

class CreateUserRequestSchema(Dict):
    username: str
    password: str

class LoginRequestSchema(Dict):
    username: str
    password: str

class JoinGameRequestSchema(Dict):
    user_uuid: str
    world_name: Optional[str] = None
    world_id: Optional[str] = None
    character_name: Optional[str] = None
    character_id: Optional[str] = None

class LeaveGameRequestSchema(Dict):
    user_uuid: str

class InteractionRequestSchema(Dict):
    user_uuid: str
    world_id: Optional[str] = None
    character_id: Optional[str] = None
    interaction_source: str  # "ai" or "user"
    text: str

@users_bp.route("/create", methods=["POST"])
def create_user():
    """Create a new user"""
    data: CreateUserRequestSchema = request.get_json()

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["username", "password"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400
    
    # Check if user already exists
    existing_user = client.find_one("users", {"username": data["username"]})
    if existing_user:
        return jsonify({"error": "User already exists"}), 409
    
    # Hash password and create user
    hashed_password = hashpw(data["password"].encode(), gensalt()).decode()
    new_uuid = str(uuid4())

    user = UserSchema(
        username=data["username"],
        password=hashed_password,
        uuid=new_uuid,
        created_at=datetime.datetime.utcnow(),
    )

    # Convert to dict properly to handle enum serialization
    user_dict = user.to_dict()
    
    # Insert user with validation
    user_id = client.insert_one("users", user_dict)
    if not user_id:
        return jsonify({"error": "Failed to create user"}), 500

    return jsonify({
        "message": "User created successfully", 
        "user_id": user.uuid,
        "username": user.username
    }), 201

@users_bp.route("/login", methods=["POST"])
def login_user():
    """Authenticate user and return user information"""
    data: LoginRequestSchema = request.get_json()

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["username", "password"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400
    
    # Find user by username
    user = client.find_one("users", {"username": data["username"]})
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Check password
    if not checkpw(data["password"].encode(), user["password"].encode()):
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Update last login
    client.update_one("users", 
                     {"username": data["username"]}, 
                     {"last_login": datetime.datetime.utcnow()})
    
    # Remove password from response
    user.pop("password", None)
    
    return jsonify({
        "message": "Login successful",
        "user": user
    }), 200

@users_bp.route("/add-data", methods=["POST"])
def add_data():
    """Update user's current game context (world and/or character)"""
    data: JoinGameRequestSchema = request.get_json()

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Prepare update data
    update_data = {}
    
    if "world_name" in data and data["world_name"]:
        update_data["current_world_name"] = data["world_name"]
    
    if "world_id" in data and data["world_id"]:
        update_data["current_world_id"] = data["world_id"]
    
    if "character_name" in data and data["character_name"]:
        update_data["current_character_name"] = data["character_name"]
    
    if "character_id" in data and data["character_id"]:
        update_data["current_character_id"] = data["character_id"]
    
    # At least one field should be provided
    if not update_data:
        return jsonify({"error": "At least one game context field must be provided"}), 400
    
    # Update user
    success = client.update_one("users", {"uuid": data["user_uuid"]}, update_data)
    if not success:
        return jsonify({"error": "Failed to update user game context"}), 500
    
    return jsonify({
        "message": "User game context updated successfully",
        "updated_fields": list(update_data.keys())
    }), 200

@users_bp.route("/clear-data", methods=["POST"])
def clear_data():
    """Remove user's current game context"""
    data: LeaveGameRequestSchema = request.get_json()

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Clear game context
    update_data = {
        "current_world_name": None,
        "current_world_id": None,
        "current_character_name": None,
        "current_character_id": None
    }
    
    # Update user
    success = client.update_one("users", {"uuid": data["user_uuid"]}, update_data)
    if not success:
        return jsonify({"error": "Failed to clear user game context"}), 500
    
    return jsonify({
        "message": "User game context cleared successfully"
    }), 200

@users_bp.route("/interaction", methods=["POST"])
def save_interaction():
    """Save a new user or AI interaction"""
    data: InteractionRequestSchema = request.get_json()

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid", "interaction_source", "message"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400
    
    # Validate interaction source
    if data["interaction_source"] not in ["user", "ai"]:
        return jsonify({"error": "interaction_source must be either 'user' or 'ai'"}), 400
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Create interaction document
    interaction = InteractionSchema(
        user_uuid=data["user_uuid"],
        world_id=data.get("world_id", None),
        character_id=data.get("character_id", None),
        interaction_source=data["interaction_source"],
        message=data["message"],
        timestamp=datetime.datetime.utcnow()
    )
    
    # Insert interaction
    interaction_id = client.insert_one("ai_interactions", interaction.to_dict())
    if not interaction_id:
        return jsonify({"error": "Failed to save interaction"}), 500
    
    return jsonify({
        "message": "Interaction saved successfully",
        "interaction_id": interaction_id
    }), 201

@users_bp.route("/get-interactions", methods=["GET"])
def get_interactions():
    """Get user interactions filtered by user_uuid, world_id, and character_id"""
    user_uuid = request.args.get("user_uuid")
    world_id = request.args.get("world_id")
    character_id = request.args.get("character_id")
    limit = request.args.get("limit", type=int)
    
    # Validate required parameters
    if not user_uuid:
        return jsonify({"error": "user_uuid parameter is required"}), 400
    
    if not world_id:
        return jsonify({"error": "world_id parameter is required"}), 400
    
    if not character_id:
        return jsonify({"error": "character_id parameter is required"}), 400
    
    # Check if user exists
    user = client.find_one("users", {"uuid": user_uuid})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Build filter
    filter_dict = {
        "user_uuid": user_uuid,
        "world_id": world_id,
        "character_id": character_id
    }
    
    # Get interactions (sorted by timestamp descending)
    try:
        collection = client.get_collection("ai_interactions")
        cursor = collection.find(filter_dict).sort("timestamp", -1)
        
        if limit and limit > 0:
            cursor = cursor.limit(limit)
        
        interactions = []
        for interaction in cursor:
            # Convert ObjectId to string for JSON serialization
            interaction["_id"] = str(interaction["_id"])
            interactions.append(interaction)
        
        return jsonify({
            "message": f"Found {len(interactions)} interactions",
            "interactions": interactions,
            "filters": filter_dict
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve interactions: {str(e)}"}), 500

