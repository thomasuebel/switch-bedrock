#!/bin/sh
set -e

GEYSER_DIR="/app/geyser"
CONFIG_DIR="/app/config"
GEYSER_JAR="$GEYSER_DIR/Geyser.jar"
DOWNLOAD_URL="https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/standalone"

# Download GeyserMC if not present
if [ ! -f "$GEYSER_JAR" ]; then
    echo "Downloading GeyserMC Standalone..."
    mkdir -p "$GEYSER_DIR"
    wget -q -O "$GEYSER_JAR" "$DOWNLOAD_URL"
    echo "Download complete."
fi

# Copy default config if not present
if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    echo "Creating default config..."
    cp /app/config-default/config.yml "$CONFIG_DIR/config.yml"
fi

# Run GeyserMC in a restart loop (background)
echo "Starting GeyserMC..."
(
    while true; do
        cd "$GEYSER_DIR"
        java -jar Geyser.jar --config "$CONFIG_DIR/config.yml" || true
        echo "GeyserMC exited, restarting in 1s..."
        sleep 1
    done
) &

# Start Flask web UI (foreground)
echo "Starting web UI on port 5000..."
cd /app/web
exec python app.py
