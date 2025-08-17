from flask import Blueprint, jsonify, request
import datetime

# Create the system blueprint
system_bp = Blueprint("system", __name__)


@system_bp.route("/health", methods=["GET"])
def health_check():
    """Health check verification for the API"""
    # Get language from query parameters (default to 'en') 
    language = request.args.get('lang', 'en')
    if language not in ['fr', 'en']:
        language = 'en'
    
    # Localized health status messages
    status_messages = {
        "en": "healthy",
        "fr": "sain"
    }
    
    return jsonify(
        {
            "status": status_messages.get(language, "healthy"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "odyssai-core",
            "version": "1.0.0",
            "language": language
        }
    ), 200
