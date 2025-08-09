import os
from flask import Flask, render_template
from odyssai_core.routes.api import api_bp

app = Flask(__name__, template_folder="templates", static_folder="static")

# Register the API blueprint with the /api prefix
app.register_blueprint(api_bp, url_prefix="/api")


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
