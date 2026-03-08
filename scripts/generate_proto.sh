#!/usr/bin/env bash
# Generate Python bindings from .proto files.
# Run this after any .proto modification.
#
# Usage: bash scripts/generate_proto.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$REPO_ROOT/proto"
OUT_DIR="$REPO_ROOT/shared/proto_generated"

if [ ! -d "$PROTO_DIR" ]; then
    echo "Error: proto directory not found at $PROTO_DIR" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# Locate the well-known types shipped with grpcio-tools
GRPC_PROTO_DIR="$(python3 -c 'import grpc_tools; import os; print(os.path.join(os.path.dirname(grpc_tools.__file__), "_proto"))')"

python3 -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    -I"$GRPC_PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --pyi_out="$OUT_DIR" \
    "$PROTO_DIR"/*.proto

# Create __init__.py that re-exports all generated modules
cat > "$OUT_DIR/__init__.py" << 'PYEOF'
"""Auto-generated Protobuf bindings.

Do not edit manually. Regenerate with::

    bash scripts/generate_proto.sh
"""
PYEOF

echo "Proto generation complete: $OUT_DIR"
ls -la "$OUT_DIR"
