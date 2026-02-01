<#
.SYNOPSIS
    Generates Python proto files from Go proto definitions.

.DESCRIPTION
    This script generates Python protobuf and gRPC files from the engine.proto
    definition in jeeves-core. It handles the cross-repo generation and fixes
    the import statements to use relative imports.

.EXAMPLE
    .\scripts\Generate-Protos.ps1

.NOTES
    Prerequisites:
    - Python with grpcio-tools installed (pip install grpcio-tools)
    - jeeves-core and jeeves-airframe in the same parent directory
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$GoProtoDir = Join-Path $RepoRoot "jeeves-core\coreengine\proto"
$PyProtoOut = Join-Path $RepoRoot "jeeves-airframe\jeeves_infra\protocols"

Write-Host "=== Proto Generation Script ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repository root: $RepoRoot"
Write-Host "Proto source:    $GoProtoDir"
Write-Host "Python output:   $PyProtoOut"
Write-Host ""

# Validation
if (-not (Test-Path (Join-Path $GoProtoDir "engine.proto"))) {
    Write-Error "engine.proto not found at $GoProtoDir"
    exit 1
}

if (-not (Test-Path $PyProtoOut)) {
    Write-Error "Output directory not found at $PyProtoOut"
    exit 1
}

# Step 1: Generate protos
Write-Host "=== Step 1: Generating Python protos ===" -ForegroundColor Yellow
Push-Location $GoProtoDir
try {
    python -m grpc_tools.protoc -I. `
        --python_out="$PyProtoOut" `
        --grpc_python_out="$PyProtoOut" `
        engine.proto

    if ($LASTEXITCODE -ne 0) {
        Write-Error "protoc failed with exit code $LASTEXITCODE"
        exit 1
    }
    Write-Host "  Generated engine_pb2.py and engine_pb2_grpc.py" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Step 2: Fix imports
Write-Host ""
Write-Host "=== Step 2: Fixing imports in engine_pb2_grpc.py ===" -ForegroundColor Yellow
$grpcFile = Join-Path $PyProtoOut "engine_pb2_grpc.py"
$content = Get-Content $grpcFile -Raw
$fixedContent = $content -replace '^import engine_pb2 as', 'from . import engine_pb2 as'
Set-Content -Path $grpcFile -Value $fixedContent -NoNewline
Write-Host "  Fixed relative import in engine_pb2_grpc.py" -ForegroundColor Green

# Step 3: Verify
Write-Host ""
Write-Host "=== Step 3: Verifying generated protos ===" -ForegroundColor Yellow
Push-Location (Join-Path $RepoRoot "jeeves-airframe")
try {
    # Check force field exists
    $verifyForce = python -c @"
from jeeves_infra.protocols import engine_pb2
req = engine_pb2.InitializeSessionRequest()
assert hasattr(req, 'force'), 'Missing force field'
print('  Proto has force field: OK')
"@
    Write-Host $verifyForce -ForegroundColor Green

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Proto verification failed - force field missing"
        exit 1
    }

    # Check gRPC imports work
    $verifyGrpc = python -c "from jeeves_infra.protocols import engine_pb2_grpc; print('  Proto gRPC imports: OK')"
    Write-Host $verifyGrpc -ForegroundColor Green

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Proto gRPC import verification failed"
        exit 1
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Proto generation complete ===" -ForegroundColor Cyan
