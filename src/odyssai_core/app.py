import os
from flask import Flask
from odyssai_core.routes.api import api_bp

app = Flask(__name__)

# Enregistrer le blueprint API avec le préfixe /api
app.register_blueprint(api_bp, url_prefix="/api")


@app.route("/")
def hello():
    return "Hello, Odyssai!"


if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 9000))
    app.run(debug=True, port=port)
