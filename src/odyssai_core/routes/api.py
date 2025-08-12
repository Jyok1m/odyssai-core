from flask import Blueprint, jsonify, request
from typing import Dict
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.config import settings  # noqa: F401
from odyssai_core.workflows import main_graph
import datetime


class CreateWorldRequestSchema(Dict):
    world_name: str
    world_genre: str
    story_directives: str


class CreateCharacterRequestSchema(Dict):
    world_id: str
    character_name: str
    character_gender: str
    character_description: str


class JoinGameRequestSchema(Dict):
    world_name: str
    character_name: str


class RegisterAnswerRequestSchema(Dict):
    world_id: str
    character_id: str
    player_answer: str


# Create the API blueprint
api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "odyssai-core",
            "version": "1.0.0",
        }
    ), 200


@api_bp.route("/check-world", methods=["GET"])
def check_world():
    world_name = request.args.get("world_name")
    world_id = request.args.get("world_id")

    if not world_name and not world_id:
        return jsonify({"error": "Either world_name or world_id parameter is required"}), 400

    state: main_graph.StateSchema = {
        "source": "api",
    }

    if world_id:
        state["world_id"] = world_id
    else:
        state["world_name"] = str(world_name).strip().lower()

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        if world_id:
            graph.add_node("check_world_exists_by_id", main_graph.check_world_exists_by_id)
            graph.set_entry_point("check_world_exists_by_id")
            graph.add_edge("check_world_exists_by_id", main_graph.END)
        else:
            graph.add_node("check_world_exists", main_graph.check_world_exists)
            graph.set_entry_point("check_world_exists")
            graph.add_edge("check_world_exists", main_graph.END)

        workflow = graph.compile()
        result = workflow.invoke(state)

        return jsonify(
            {
                "success": True,
                "exists": True,
                "world_id": result.get("world_id"),
                "world_name": result.get("world_name"),
            }
        ), 200

    except Exception as e:
        # If the world doesn't exist, the workflow will raise an exception
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            return jsonify(
                {
                    "success": True,
                    "exists": False,
                    "world_id": world_id,
                    "world_name": world_name,
                }
            ), 200
        
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500


@api_bp.route("/synopsis", methods=["GET"])
def get_synopsis():
    world_id = request.args.get("world_id")

    if not world_id:
        return jsonify({"error": "world_id parameter is required"}), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "world_id": world_id,
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # Add nodes for synopsis generation
        graph.add_node("check_world_exists_by_id", main_graph.check_world_exists_by_id)
        graph.add_node("get_world_context", main_graph.get_world_context)
        graph.add_node("get_lore_context", main_graph.get_lore_context)
        graph.add_node("get_character_context", main_graph.get_character_context)
        graph.add_node(
            "llm_generate_world_summary", main_graph.llm_generate_world_summary
        )

        # Set entry point
        graph.set_entry_point("check_world_exists_by_id")

        # Define workflow edges
        graph.add_edge("check_world_exists_by_id", "get_world_context")
        graph.add_edge("get_world_context", "get_lore_context")
        graph.add_edge("get_lore_context", "get_character_context")
        graph.add_edge("get_character_context", "llm_generate_world_summary")
        graph.add_edge("llm_generate_world_summary", main_graph.END)

        # Compile and execute workflow
        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "world_id": result.get("world_id"),
            "synopsis": result.get("world_summary"),
        }
    ), 200


@api_bp.route("/create-world", methods=["POST"])
def create_world():
    data: CreateWorldRequestSchema = request.get_json()

    validation_result = check_empty_fields(
        data, ["world_name", "world_genre", "story_directives"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "create_new_world": True,
        "world_name": str(data["world_name"]).strip().lower(),
        "world_genre": str(data["world_genre"]).strip().lower(),
        "story_directives": str(data["story_directives"]).strip().lower(),
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        graph.add_node("check_world_exists", main_graph.check_world_exists)
        graph.add_node("llm_generate_world_data", main_graph.llm_generate_world_data)
        graph.add_node("save_documents_to_chroma", main_graph.save_documents_to_chroma)
        graph.add_node("llm_generate_lore_data", main_graph.llm_generate_lore_data)
        graph.add_node(
            "llm_generate_world_summary", main_graph.llm_generate_world_summary
        )

        graph.set_entry_point("check_world_exists")

        graph.add_edge("check_world_exists", "llm_generate_world_data")
        graph.add_edge("llm_generate_world_data", "save_documents_to_chroma")
        graph.add_edge("llm_generate_lore_data", "save_documents_to_chroma")
        graph.add_conditional_edges(
            "save_documents_to_chroma",
            lambda state: "__from_world__"
            if state.get("active_step") == "world_creation"
            else "__from_lore__",
            {
                "__from_world__": "llm_generate_lore_data",
                "__from_lore__": "llm_generate_world_summary",
            },
        )
        graph.add_edge("llm_generate_world_summary", main_graph.END)

        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "world_name": result["world_name"],
            "world_id": result["world_id"],
            "synopsis": result["world_summary"],
        }
    ), 201


@api_bp.route("/create-character", methods=["POST"])
def create_character():
    data: CreateCharacterRequestSchema = request.get_json()

    validation_result = check_empty_fields(
        data,
        ["world_id", "character_name", "character_gender", "character_description"],
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400

    state: main_graph.StateSchema = {
        "source": "api",
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
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "character_name": result.get("character_name"),
            "character_id": result.get("character_id"),
            "character_description": result.get("character_context"),
            "world_id": result.get("world_id"),
        }
    ), 201


@api_bp.route("/join-game", methods=["POST"])
def join_game():
    data: JoinGameRequestSchema = request.get_json()

    validation_result = check_empty_fields(data, ["world_name", "character_name"])
    if not validation_result["result"]:
        return jsonify(validation_result), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "create_new_world": False,
        "create_new_character": False,
        "world_name": str(data["world_name"]).strip().lower(),
        "character_name": str(data["character_name"]).strip().lower(),
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # Add nodes for join game workflow
        graph.add_node("check_world_exists", main_graph.check_world_exists)
        graph.add_node("check_character_exists", main_graph.check_character_exists)
        graph.add_node("get_world_context", main_graph.get_world_context)
        graph.add_node("get_lore_context", main_graph.get_lore_context)
        graph.add_node("get_character_context", main_graph.get_character_context)
        graph.add_node("llm_generate_lore_data", main_graph.llm_generate_lore_data)
        graph.add_node("save_documents_to_chroma", main_graph.save_documents_to_chroma)
        graph.add_node(
            "llm_generate_world_summary", main_graph.llm_generate_world_summary
        )

        # Set entry point
        graph.set_entry_point("check_world_exists")

        # Define workflow edges
        graph.add_edge("check_world_exists", "check_character_exists")
        graph.add_edge("check_character_exists", "get_world_context")
        graph.add_edge("get_world_context", "get_lore_context")
        graph.add_edge("get_lore_context", "get_character_context")
        graph.add_edge("get_character_context", "llm_generate_lore_data")
        graph.add_edge("llm_generate_lore_data", "save_documents_to_chroma")
        graph.add_edge("save_documents_to_chroma", "llm_generate_world_summary")
        graph.add_edge("llm_generate_world_summary", main_graph.END)

        # Compile and execute workflow
        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "world_name": result.get("world_name"),
            "world_id": result.get("world_id"),
            "character_name": result.get("character_name"),
            "character_id": result.get("character_id"),
            "world_summary": result.get("world_summary"),
        }
    ), 200


@api_bp.route("/game-prompt", methods=["GET"])
def get_game_prompt():
    world_id = request.args.get("world_id")
    character_id = request.args.get("character_id")

    if not world_id:
        return jsonify({"error": "world_id parameter is required"}), 400

    if not character_id:
        return jsonify({"error": "character_id parameter is required"}), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "world_id": world_id,
        "character_id": character_id,
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # Add nodes for game prompt generation workflow
        graph.add_node("check_world_exists_by_id", main_graph.check_world_exists_by_id)
        graph.add_node(
            "check_character_exists_by_id", main_graph.check_character_exists_by_id
        )
        graph.add_node("get_world_context", main_graph.get_world_context)
        graph.add_node("get_lore_context", main_graph.get_lore_context)
        graph.add_node("get_character_context", main_graph.get_character_context)
        graph.add_node("get_event_context", main_graph.get_event_context)
        graph.add_node("llm_generate_next_prompt", main_graph.llm_generate_next_prompt)

        # Set entry point
        graph.set_entry_point("check_world_exists_by_id")

        # Define workflow edges
        graph.add_edge("check_world_exists_by_id", "check_character_exists_by_id")
        graph.add_edge("check_character_exists_by_id", "get_world_context")
        graph.add_edge("get_world_context", "get_lore_context")
        graph.add_edge("get_lore_context", "get_character_context")
        graph.add_edge("get_character_context", "get_event_context")
        graph.add_edge("get_event_context", "llm_generate_next_prompt")
        graph.add_edge("llm_generate_next_prompt", main_graph.END)

        # Compile and execute workflow
        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "world_id": result.get("world_id"),
            "character_id": result.get("character_id"),
            "ai_prompt": result.get("ai_question"),
        }
    ), 200


@api_bp.route("/register-answer", methods=["POST"])
def register_answer():
    data: RegisterAnswerRequestSchema = request.get_json()

    validation_result = check_empty_fields(
        data, ["world_id", "character_id", "player_answer"]
    )
    if not validation_result["result"]:
        return jsonify(validation_result), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "world_id": str(data["world_id"]).strip(),
        "character_id": str(data["character_id"]).strip(),
        "player_answer": str(data["player_answer"]).strip(),
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        # Add nodes for register answer workflow
        graph.add_node("check_world_exists_by_id", main_graph.check_world_exists_by_id)
        graph.add_node(
            "check_character_exists_by_id", main_graph.check_character_exists_by_id
        )
        graph.add_node("get_event_context", main_graph.get_event_context)
        graph.add_node("record_player_response", main_graph.record_player_response)
        graph.add_node(
            "llm_generate_immediate_event_summary",
            main_graph.llm_generate_immediate_event_summary,
        )

        # Set entry point
        graph.set_entry_point("check_world_exists_by_id")

        # Define workflow edges
        graph.add_edge("check_world_exists_by_id", "check_character_exists_by_id")
        graph.add_edge("check_character_exists_by_id", "get_event_context")
        graph.add_edge("get_event_context", "record_player_response")
        graph.add_edge("record_player_response", "llm_generate_immediate_event_summary")
        graph.add_edge("llm_generate_immediate_event_summary", main_graph.END)

        # Compile and execute workflow
        workflow = graph.compile()
        result = workflow.invoke(state)

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify(
        {
            "success": True,
            "world_id": result.get("world_id"),
            "character_id": result.get("character_id"),
            "immediate_events": result.get("immediate_events"),
        }
    ), 200
