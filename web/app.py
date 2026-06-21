"""Flask web UI for configuring GeyserMC."""

import subprocess
from flask import Flask, render_template, request, jsonify
import config_manager
import server_info
import version_manager

DEFAULT_CONFIG = "/app/config/config.yml"


def create_app(config_path=None, sources_path=None):
    app = Flask(__name__)
    app.config["CONFIG_PATH"] = config_path or DEFAULT_CONFIG
    app.config["SOURCES_PATH"] = sources_path or version_manager.DEFAULT_SOURCES_PATH

    def _sources():
        return version_manager.load_sources(app.config["SOURCES_PATH"])

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
        # Drop cached stats — they belong to the previous remote.
        server_info.clear_cache()
        return jsonify({"status": "ok"})

    @app.route("/api/status")
    def status():
        result = subprocess.run(
            ["pgrep", "-f", "Geyser.jar"],
            capture_output=True,
        )
        running = result.returncode == 0
        return jsonify({"geyser_running": running})

    @app.route("/api/server-info")
    def remote_info():
        remote = config_manager.get_remote_server(app.config["CONFIG_PATH"])
        return jsonify(server_info.query(remote["address"], remote["port"]))

    @app.route("/api/versions")
    def versions():
        return jsonify(version_manager.get_status(_sources()))

    @app.route("/api/update/<project>", methods=["POST"])
    def update(project):
        try:
            meta = version_manager.download(project, _sources())
        except version_manager.UpdateError as e:
            return jsonify({"error": str(e)}), 400
        subprocess.run(["pkill", "-f", "Geyser.jar"], check=False)
        return jsonify({
            "status": "ok",
            "build": meta.get("build"),
            "version": meta.get("version"),
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
