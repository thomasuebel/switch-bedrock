#!/bin/bash
set -e

APP_NAME="switch-bedrock"

# Extract version from git tag (strip leading 'v')
VERSION="${GITHUB_REF_NAME:-dev}"
VERSION="${VERSION#v}"

echo "Building release packages for $APP_NAME v$VERSION..."

# Produce a versioned docker-compose.yml (pin :latest → :$VERSION)
sed "s|ghcr.io/thomasuebel/switch-bedrock:latest|ghcr.io/thomasuebel/switch-bedrock:${VERSION}|g" \
    docker-compose.yml > docker-compose.release.yml

# Generic ZIP (flat structure)
zip "${APP_NAME}-generic.zip" docker-compose.release.yml
echo "Created ${APP_NAME}-generic.zip"

# CasaOS ZIP (Apps/<app-name>/ structure)
mkdir -p "Apps/${APP_NAME}"
cp docker-compose.release.yml "Apps/${APP_NAME}/docker-compose.yml"
zip -r "${APP_NAME}-casaos.zip" "Apps/"
rm -rf Apps/
rm docker-compose.release.yml

echo "Done."
