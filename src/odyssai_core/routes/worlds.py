from flask import Blueprint, jsonify, request
from typing import Dict
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.workflows import main_graph

# Create the worlds blueprint
worlds_bp = Blueprint("worlds", __name__)


class CreateWorldRequestSchema(Dict):
    world_name: str
    world_genre: str
    story_directives: str


@worlds_bp.route("/", methods=["GET"])
def list_worlds():
    """Get a list of all created worlds"""
    try:
        worlds_list = main_graph.get_all_worlds()
        
        return jsonify({
            "success": True,
            "worlds": worlds_list,
            "count": len(worlds_list)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e), 
            "error_type": e.__class__.__name__
        }), 500


@worlds_bp.route("/", methods=["POST"])
def create_world():
    """Create a new narrative world"""
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


@worlds_bp.route("/<world_id>/synopsis", methods=["GET"])
def get_world_synopsis(world_id: str):
    """Get a synopsis of an existing world"""
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


@worlds_bp.route("/check", methods=["GET"])
def check_world():
    """Check if a world exists by name or ID"""
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
