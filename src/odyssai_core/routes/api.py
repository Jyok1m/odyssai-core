from flask import Blueprint, jsonify, request
from typing import Dict, Union
from odyssai_core.modules.validators import check_empty_fields
from odyssai_core.config import settings  # noqa: F401
from odyssai_core.workflows import main_graph
import datetime

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


@api_bp.route("/create-world", methods=["POST"])
def create_world():
    data: Dict[str, Union[str, int]] = request.get_json()

    validation_result = check_empty_fields(data, ["world_name"])
    if not validation_result["result"]:
        return jsonify(validation_result), 400

    state: main_graph.StateSchema = {
        "source": "api",
        "create_new_world": True,
        "world_name": str(data["world_name"]).strip().lower(),
    }

    try:
        graph = main_graph.StateGraph(main_graph.StateSchema)

        graph.add_node("check_world_exists", main_graph.check_world_exists)
        graph.set_entry_point("check_world_exists")
        graph.add_edge("check_world_exists", main_graph.END)

        workflow = graph.compile()
        result = workflow.invoke(state, config={"recursion_limit": 9999})

    except Exception as e:
        return jsonify(
            {"success": False, "error": str(e), "error_type": e.__class__.__name__}
        ), 500

    return jsonify({"success": True, "workflow": result}), 201
