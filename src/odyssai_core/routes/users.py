from flask import Blueprint, jsonify, request
from typing import Dict, Optional
from odyssai_core.db import MongoDBClient
from odyssai_core.db.schemas import UserSchema, InteractionSchema
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.utils.i18n import (
    create_error_response, 
    create_success_response
)
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

class UpdateLanguageRequestSchema(Dict):
    user_uuid: str
    language: Optional[str] = None

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
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["username", "password"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user already exists
    existing_user = client.find_one("users", {"username": data["username"]})
    if existing_user:
        error_response, status_code = create_error_response(
            language, "user_already_exists", 409
        )
        return jsonify(error_response), status_code
    
    # Hash password and create user
    hashed_password = hashpw(data["password"].encode(), gensalt()).decode()
    new_uuid = str(uuid4())

    user = UserSchema(
        username=data["username"],
        password=hashed_password,
        uuid=new_uuid,
        created_at=datetime.datetime.utcnow(),
        language=language,  # Add language to user schema
    )

    # Convert to dict properly to handle enum serialization
    user_dict = user.to_dict()
    
    # Insert user with validation
    user_id = client.insert_one("users", user_dict)
    if not user_id:
        error_response, status_code = create_error_response(
            language, "failed_create_user", 500
        )
        return jsonify(error_response), status_code

    success_response, status_code = create_success_response(
        language, 
        "user_created", 
        {
            "user_id": user.uuid,
            "username": user.username,
            "language": language
        }, 
        201
    )
    return jsonify(success_response), status_code

@users_bp.route("/login", methods=["POST"])
def login_user():
    """Authenticate user and return user information"""
    data: LoginRequestSchema = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["username", "password"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Find user by username
    user = client.find_one("users", {"username": data["username"]})
    if not user:
        error_response, status_code = create_error_response(
            language, "invalid_credentials", 401
        )
        return jsonify(error_response), status_code
    
    # Check password
    if not checkpw(data["password"].encode(), user["password"].encode()):
        error_response, status_code = create_error_response(
            user["language"], "invalid_credentials", 401
        )
        return jsonify(error_response), status_code
    
    # Update last login and language preference
    client.update_one("users", 
                     {"username": data["username"]}, 
                     {"last_login": datetime.datetime.utcnow()})
    
    # Remove password from response
    user.pop("password", None)
    
    success_response, status_code = create_success_response(
        user["language"], 
        "login_successful", 
        {"user": user}, 
        200
    )
    return jsonify(success_response), status_code

@users_bp.route("/check-username", methods=["GET"])
def check_username_exists():
    """Check if a username exists in the database"""
    username = request.args.get('username')
    
    # Validate required parameter
    if not username:
        return jsonify({"exists": False}), 404
    
    # Check if user exists
    existing_user = client.find_one("users", {"username": username})
    
    return jsonify({"exists": bool(existing_user)}), 200

@users_bp.route("/add-data", methods=["POST"])
def add_data():
    """Update user's current game context (world and/or character)"""
    data: JoinGameRequestSchema = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
    # Prepare update data
    update_data = {}

    if "world_name" in data and data["world_name"]:
        update_data["current_world_name"] = data["world_name"]
    
    if "world_id" in data and data["world_id"]:
        update_data["current_world_id"] = data["world_id"]

    if "world_genre" in data and data["world_genre"]:
        update_data["current_world_genre"] = data["world_genre"]

    if "story_directives" in data and data["story_directives"]:
        update_data["current_story_directives"] = data["story_directives"]

    if "character_name" in data and data["character_name"]:
        update_data["current_character_name"] = data["character_name"]
    
    if "character_id" in data and data["character_id"]:
        update_data["current_character_id"] = data["character_id"]

    if "character_genre" in data and data["character_genre"]:
        update_data["current_character_genre"] = data["character_genre"]

    if "character_description" in data and data["character_description"]:
        update_data["current_character_description"] = data["character_description"]
    
    # At least one field should be provided
    if not update_data:
        error_response, status_code = create_error_response(
            language, "missing_game_context", 400
        )
        return jsonify(error_response), status_code
    
    print(data["user_uuid"], update_data)
    # Update user
    success = client.update_one("users", {"uuid": data["user_uuid"]}, update_data)
    if not success:
        error_response, status_code = create_error_response(
            language, "failed_update_user", 500
        )
        return jsonify(error_response), status_code
    
    success_response, status_code = create_success_response(
        language, 
        "user_context_updated", 
        {"updated_fields": list(update_data.keys())}, 
        200
    )
    return jsonify(success_response), status_code

@users_bp.route("/update-language", methods=["POST"])
def update_language():
    """Update user's language preference"""
    data = request.get_json()
    
    # Get language from query parameters or body
    language = request.args.get('lang') or data.get('language', 'en')
    if language not in ['fr', 'en']:
        error_response, status_code = create_error_response(
            'en', "invalid_language", 400
        )
        return jsonify(error_response), status_code

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
    # Update user language
    success = client.update_one("users", 
                               {"uuid": data["user_uuid"]}, 
                               {"language": language})
    if not success:
        error_response, status_code = create_error_response(
            language, "failed_update_language", 500
        )
        return jsonify(error_response), status_code
    
    success_response, status_code = create_success_response(
        language, 
        "language_updated", 
        {
            "user_uuid": data["user_uuid"],
            "language": language
        }, 
        200
    )
    return jsonify(success_response), status_code

@users_bp.route("/clear-data", methods=["DELETE"])
def clear_data():
    """Remove user's current game context"""
    data: LeaveGameRequestSchema = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
    # Clear game context
    update_data = {
        "current_is_new_world": True,
        "current_world_id": "",
        "current_world_name": "",
        "current_world_genre": "",
        "current_story_directives": "",
        "current_is_new_character": True,
        "current_character_id": "",
        "current_character_name": "",
        "current_character_genre": "",
        "current_character_description": "",
    }
    
    # Update user
    success = client.update_one("users", {"uuid": data["user_uuid"]}, update_data)
    if not success:
        error_response, status_code = create_error_response(
            language, "failed_clear_context", 500
        )
        return jsonify(error_response), status_code
    
    success_response, status_code = create_success_response(
        language, "context_cleared", {}, 200
    )
    return jsonify(success_response), status_code

@users_bp.route("/interaction", methods=["POST"])
def save_interaction():
    """Save a new user or AI interaction"""
    data: InteractionRequestSchema = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid", "interaction_source", "message"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    # Validate interaction source
    if data["interaction_source"] not in ["user", "ai"]:
        error_response, status_code = create_error_response(
            language, "invalid_interaction_source", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user exists
    user = client.find_one("users", {"uuid": data["user_uuid"]})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
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
        error_response, status_code = create_error_response(
            language, "failed_save_interaction", 500
        )
        return jsonify(error_response), status_code
    
    success_response, status_code = create_success_response(
        language, 
        "interaction_saved", 
        {"interaction_id": interaction_id}, 
        201
    )
    return jsonify(success_response), status_code

@users_bp.route("/get-interactions", methods=["GET"])
def get_interactions():
    """Get user interactions filtered by user_uuid, world_id, and character_id"""
    user_uuid = request.args.get("user_uuid")
    world_id = request.args.get("world_id")
    character_id = request.args.get("character_id")
    limit = request.args.get("limit", type=int)
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'
    
    # Validate required parameters
    if not user_uuid:
        error_response, status_code = create_error_response(
            language, "user_uuid_required", 400
        )
        return jsonify(error_response), status_code
    
    # Check if user exists
    user = client.find_one("users", {"uuid": user_uuid})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
    # Build filter
    filter_dict = {
        "user_uuid": user_uuid,
    }

    if world_id:
        filter_dict["world_id"] = world_id

    if character_id:
        filter_dict["character_id"] = character_id

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
        
        success_response, status_code = create_success_response(
            language, 
            "interactions_found", 
            {
                "interactions": interactions,
                "filters": filter_dict
            }, 
            200, 
            count=len(interactions)
        )
        return jsonify(success_response), status_code
        
    except Exception as e:
        error_response, status_code = create_error_response(
            language, "failed_retrieve_interactions", 500, error=str(e)
        )
        return jsonify(error_response), status_code

@users_bp.route("/delete-interactions", methods=["DELETE"])
def delete_user_interactions():
    """Delete all interactions for a specific user"""
    data = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    # Validate required fields
    validation_result = check_empty_fields(
        data, ["user_uuid"]
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code
    
    user_uuid = data["user_uuid"]
    
    # Check if user exists
    user = client.find_one("users", {"uuid": user_uuid})
    if not user:
        error_response, status_code = create_error_response(
            language, "user_not_found", 404
        )
        return jsonify(error_response), status_code
    
    try:
        # Delete all interactions for this user
        collection = client.get_collection("ai_interactions")
        delete_result = collection.delete_many({"user_uuid": user_uuid})
        
        success_response, status_code = create_success_response(
            language, 
            "interactions_deleted", 
            {
                "deleted_count": delete_result.deleted_count,
                "user_uuid": user_uuid
            }, 
            200, 
            count=delete_result.deleted_count,
            user_uuid=user_uuid
        )
        return jsonify(success_response), status_code
        
    except Exception as e:
        error_response, status_code = create_error_response(
            language, "failed_delete_interactions", 500, error=str(e)
        )
        return jsonify(error_response), status_code

