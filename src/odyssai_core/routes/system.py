from flask import Blueprint, jsonify
import datetime

# Create the system blueprint
system_bp = Blueprint("system", __name__)


@system_bp.route("/health", methods=["GET"])
def health_check():
    """Health check verification for the API"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "odyssai-core",
            "version": "1.0.0",
        }
    ), 200
