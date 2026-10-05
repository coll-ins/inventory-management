"""Application factory for the inventory API."""
from flask import Flask, jsonify

from .routes import bp
from .storage import InventoryStore


def create_app():
    app = Flask(__name__)
    # One store per app instance keeps tests isolated from each other.
    app.extensions["store"] = InventoryStore()
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    return app
