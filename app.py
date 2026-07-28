import importlib

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from config.operations import OPERATIONS

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", operations=OPERATIONS)


@app.route("/api/run", methods=["POST"])
def run_operation():
    data = request.get_json(silent=True) or {}
    operation_key = data.get("operation")

    if operation_key not in OPERATIONS:
        return jsonify({"success": False, "message": "Operacao invalida."}), 400

    module = importlib.import_module(f"automation.{operation_key}")
    result = module.run(headless=True)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
