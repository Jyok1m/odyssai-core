from flask import Blueprint, jsonify, request
from typing import Dict
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.utils.i18n import (
    create_error_response, 
    create_success_response
)
from odyssai_core.workflows import main_graph

# Create the characters blueprint
characters_bp = Blueprint("characters", __name__)


class CreateCharacterRequestSchema(Dict):
    world_id: str
    character_name: str
    character_gender: str
    character_description: str
#

@characters_bp.route("/", methods=["POST"])
def create_character():
    """Create a new narrative character"""
    data: CreateCharacterRequestSchema = request.get_json()
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    validation_result = check_empty_fields(
        data,
        ["world_id", "character_name", "character_gender", "character_description"],
    )
    if not validation_result["result"]:
        error_response, status_code = create_error_response(
            language, "missing_fields", 400
        )
        return jsonify(error_response), status_code

    state: main_graph.StateSchema = {
        "source": "api",
        "user_language": language,  # Add language to state
        "create_new_character": True,
        "world_id": str(data["world_id"]).strip(),
        "character_name": str(data["character_name"]).strip().lower(),
        "character_gender": str(data["character_gender"]).strip().lower(),
        "character_description": str(data["character_description"]).strip().lower(),
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # Add nodes for character creation workflow
        graph.add_node("check_character_exists", main_graph.check_character_exists)
        graph.add_node("get_world_context", main_graph.get_world_context)
        graph.add_node("get_lore_context", main_graph.get_lore_context)
        graph.add_node(
            "llm_generate_character_data", main_graph.llm_generate_character_data
        )
        graph.add_node("save_documents_to_chroma", main_graph.save_documents_to_chroma)

        # Set entry point
        graph.set_entry_point("check_character_exists")

        # Define workflow edges
        graph.add_edge("check_character_exists", "get_world_context")
        graph.add_edge("get_world_context", "get_lore_context")
        graph.add_edge("get_lore_context", "llm_generate_character_data")
        graph.add_edge("llm_generate_character_data", "save_documents_to_chroma")
        graph.add_edge("save_documents_to_chroma", main_graph.END)

        # Compile and execute workflow
        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        error_response, status_code = create_error_response(
            language, "internal_error", 500
        )
        error_response["error_details"] = str(e)
        error_response["error_type"] = e.__class__.__name__
        return jsonify(error_response), status_code

    success_response, status_code = create_success_response(
        language,
        "character_created",
        {
            "character_name": result.get("character_name"),
            "character_id": result.get("character_id"),
            "character_description": result.get("character_context"),
            "world_id": result.get("world_id")
        },
        201
    )
    return jsonify(success_response), status_code


@characters_bp.route("/check", methods=["GET"])
def check_character():
    """Check if a character exists by name or ID"""
    world_id = request.args.get("world_id")
    character_name = request.args.get("character_name")
    character_id = request.args.get("character_id")
    
    # Get language from query parameters (default to 'en')
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'

    if not world_id:
        error_response, status_code = create_error_response(
            language, "world_id_required", 400
        )
        return jsonify(error_response), status_code

    if not character_name and not character_id:
        error_response, status_code = create_error_response(
            language, "character_name_or_id_required", 400
        )
        return jsonify(error_response), status_code

    state: main_graph.StateSchema = {
        "source": "api",
        "user_language": language,
        "world_id": world_id,
    }

    if character_id:
        state["character_id"] = character_id
    else:
        state["character_name"] = str(character_name).strip().lower()

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # First check if the world exists
        graph.add_node("check_world_exists_by_id", main_graph.check_world_exists_by_id)
        
        if character_id:
            graph.add_node("check_character_exists_by_id", main_graph.check_character_exists_by_id)
            graph.set_entry_point("check_world_exists_by_id")
            graph.add_edge("check_world_exists_by_id", "check_character_exists_by_id")
            graph.add_edge("check_character_exists_by_id", main_graph.END)
        else:
            graph.add_node("check_character_exists", main_graph.check_character_exists)
            graph.set_entry_point("check_world_exists_by_id")
            graph.add_edge("check_world_exists_by_id", "check_character_exists")
            graph.add_edge("check_character_exists", main_graph.END)

        workflow = graph.compile()
        result = workflow.invoke(state)

        success_response, status_code = create_success_response(
            language,
            "character_found",
            {
                "exists": True,
                "world_id": result.get("world_id"),
                "character_id": result.get("character_id"),
                "character_name": result.get("character_name")
            },
            200
        )
        return jsonify(success_response), status_code

    except Exception as e:
        # If the character doesn't exist, the workflow will raise an exception
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            success_response, status_code = create_success_response(
                language,
                "character_not_found",
                {
                    "exists": False,
                    "world_id": world_id,
                    "character_id": character_id,
                    "character_name": character_name
                },
                200
            )
            return jsonify(success_response), status_code
        
        error_response, status_code = create_error_response(
            language, "internal_error", 500
        )

        error_response["error_details"] = str(e)
        error_response["error_type"] = e.__class__.__name__
        return jsonify(error_response), status_code
