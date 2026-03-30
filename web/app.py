"""Flask web UI for configuring GeyserMC."""

import subprocess
from flask import Flask, render_template, request, jsonify
import config_manager

DEFAULT_CONFIG = "/app/config/config.yml"


def create_app(config_path=None):
    app = Flask(__name__)
    app.config["CONFIG_PATH"] = config_path or DEFAULT_CONFIG

    @app.route("/")
    def index():
        server = config_manager.get_remote_server(app.config["CONFIG_PATH"])
        return render_template("index.html", server=server)

    @app.route("/api/config", methods=["POST"])
    def update_config():
        data = request.get_json() or {}
        try:
            config_manager.set_remote_server(
                app.config["CONFIG_PATH"],
                data.get("address", ""),
                data.get("port", 25565),
                data.get("auth_type", "offline"),
            )
        except (ValueError, TypeError) as e:
            return jsonify({"error": str(e)}), 400

        # Kill GeyserMC so the entrypoint loop restarts it with new config
        subprocess.run(["pkill", "-f", "Geyser.jar"], check=False)
        return jsonify({"status": "ok"})

    @app.route("/api/status")
    def status():
        result = subprocess.run(
            ["pgrep", "-f", "Geyser.jar"],
            capture_output=True,
        )
        running = result.returncode == 0
        return jsonify({"geyser_running": running})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
