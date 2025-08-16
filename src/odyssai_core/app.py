import os
from flask import Flask, render_template
from flask_cors import CORS
from odyssai_core.routes.system import system_bp
from odyssai_core.routes.worlds import worlds_bp
from odyssai_core.routes.characters import characters_bp
from odyssai_core.routes.gameplay import gameplay_bp
from odyssai_core.routes.users import users_bp


app = Flask(__name__, template_folder="templates", static_folder="static")

# Configure CORS
CORS(app)

# Register the blueprints with appropriate prefixes
app.register_blueprint(system_bp, url_prefix="/api")
app.register_blueprint(worlds_bp, url_prefix="/api/worlds")
app.register_blueprint(characters_bp, url_prefix="/api/characters")
app.register_blueprint(gameplay_bp, url_prefix="/api/game")
app.register_blueprint(users_bp, url_prefix="/api/users")


@app.route("/")
def landing_page():
    """
    Landing page with documentation
    """
    base_url = f"http://localhost:{os.environ.get('BACKEND_PORT', 9000)}"
    return render_template("index.html", base_url=base_url)


if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 9000))
    app.run(debug=True, port=port)
