#!/bin/bash
set -e

APP_NAME="switch-bedrock"

# Extract version from git tag (strip leading 'v')
VERSION="${GITHUB_REF_NAME:-dev}"
VERSION="${VERSION#v}"

echo "Building release packages for $APP_NAME v$VERSION..."

# Generic ZIP (flat structure)
zip "${APP_NAME}-generic.zip" docker-compose.yml
echo "Created ${APP_NAME}-generic.zip"

# CasaOS ZIP (Apps/<app-name>/ structure)
mkdir -p "Apps/${APP_NAME}"
cp docker-compose.yml "Apps/${APP_NAME}/docker-compose.yml"
zip -r "${APP_NAME}-casaos.zip" "Apps/"
rm -rf Apps/
echo "Created ${APP_NAME}-casaos.zip"

echo "Done."
