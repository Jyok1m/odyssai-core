from flask import Blueprint, jsonify, request
from typing import Dict
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.workflows import main_graph

# Create the gameplay blueprint
gameplay_bp = Blueprint("gameplay", __name__)


class JoinGameRequestSchema(Dict):
    world_name: str
    character_name: str


class RegisterAnswerRequestSchema(Dict):
    world_id: str
    character_id: str
    player_answer: str


@gameplay_bp.route("/join", methods=["POST"])
def join_game():
    """Join an existing game world"""
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


@gameplay_bp.route("/prompt", methods=["GET"])
def get_game_prompt():
    """Get game instructions/prompt for the player"""
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


@gameplay_bp.route("/action", methods=["POST"])
def register_player_action():
    """Register player's answer/response to the game prompt"""
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
