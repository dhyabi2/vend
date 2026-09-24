#!/bin/bash
# Build vend-client from vend_client_src/ and copy artifacts to dist/
set -euo pipefail

VERSION="${1:-0.1.0}"
DIST_DIR="/root/vend/dist"
SRC_DIR="/root/vend/vend_client_src"

rm -rf "$DIST_DIR"

BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

# Copy the entire source tree to build dir
cp -r "$SRC_DIR/"* "$BUILD_DIR/"

cd "$BUILD_DIR"

# Pin the tagged version
sed -i "s/version = \"0.1.0\"/version = \"$VERSION\"/" pyproject.toml

# Build sdist + wheel
/root/vend/.venv/bin/python -m build --sdist --wheel .
mkdir -p "$DIST_DIR"
cp dist/* "$DIST_DIR/"
echo "---"
echo "Built vend-client $VERSION:"
ls -la "$DIST_DIR/"