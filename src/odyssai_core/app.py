import os
from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, Odyssai!"


if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 9000))
    app.run(debug=True, port=port)
