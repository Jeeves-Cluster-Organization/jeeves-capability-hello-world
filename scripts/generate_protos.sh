#!/bin/bash
# Proto Generation Script
# Generates Python proto files from Go proto definitions
#
# Usage: ./scripts/generate_protos.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
GO_PROTO_DIR="$REPO_ROOT/jeeves-core/coreengine/proto"
PY_PROTO_OUT="$REPO_ROOT/jeeves-airframe/jeeves_infra/protocols"

echo "=== Proto Generation Script ==="
echo ""
echo "Repository root: $REPO_ROOT"
echo "Proto source:    $GO_PROTO_DIR"
echo "Python output:   $PY_PROTO_OUT"
echo ""

# Validation
if [[ ! -f "$GO_PROTO_DIR/engine.proto" ]]; then
    echo "ERROR: engine.proto not found at $GO_PROTO_DIR" >&2
    exit 1
fi

if [[ ! -d "$PY_PROTO_OUT" ]]; then
    echo "ERROR: Output directory not found at $PY_PROTO_OUT" >&2
    exit 1
fi

# Step 1: Generate protos
echo "=== Step 1: Generating Python protos ==="
cd "$GO_PROTO_DIR"
python -m grpc_tools.protoc \
    -I. \
    --python_out="$PY_PROTO_OUT" \
    --grpc_python_out="$PY_PROTO_OUT" \
    engine.proto
echo "  Generated engine_pb2.py and engine_pb2_grpc.py"

# Step 2: Fix imports
echo ""
echo "=== Step 2: Fixing imports in engine_pb2_grpc.py ==="
# The generated grpc file uses absolute import, but we need relative import
# Change: import engine_pb2 as engine__pb2
# To:     from . import engine_pb2 as engine__pb2

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires empty string for -i
    sed -i '' 's/^import engine_pb2 as/from . import engine_pb2 as/' \
        "$PY_PROTO_OUT/engine_pb2_grpc.py"
else
    # Linux sed
    sed -i 's/^import engine_pb2 as/from . import engine_pb2 as/' \
        "$PY_PROTO_OUT/engine_pb2_grpc.py"
fi
echo "  Fixed relative import in engine_pb2_grpc.py"

# Step 3: Verify
echo ""
echo "=== Step 3: Verifying generated protos ==="
cd "$REPO_ROOT/jeeves-airframe"

python -c "
from jeeves_infra.protocols import engine_pb2
req = engine_pb2.InitializeSessionRequest()
assert hasattr(req, 'force'), 'Missing force field - proto not regenerated correctly!'
print('  Proto has force field: OK')
"

python -c "from jeeves_infra.protocols import engine_pb2_grpc; print('  Proto gRPC imports: OK')"

echo ""
echo "=== Proto generation complete ==="
