from flask import Blueprint, jsonify
import datetime

# Créer le blueprint API
api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Route de vérification de santé du serveur
    Retourne le statut de santé et des informations sur le serveur
    """
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "odyssai-core",
            "version": "1.0.0",
        }
    ), 200
