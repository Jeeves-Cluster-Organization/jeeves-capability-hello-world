@echo off
setlocal enabledelayedexpansion

REM Proto Generation Script for Windows
REM Generates Python proto files from Go proto definitions
REM
REM Usage: scripts\generate_protos.bat

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
set GO_PROTO_DIR=%REPO_ROOT%\jeeves-core\coreengine\proto
set PY_PROTO_OUT=%REPO_ROOT%\jeeves-airframe\jeeves_infra\protocols

echo === Proto Generation Script ===
echo.
echo Repository root: %REPO_ROOT%
echo Proto source:    %GO_PROTO_DIR%
echo Python output:   %PY_PROTO_OUT%
echo.

REM Check that proto directory exists
if not exist "%GO_PROTO_DIR%\engine.proto" (
    echo ERROR: engine.proto not found at %GO_PROTO_DIR%
    exit /b 1
)

REM Check that output directory exists
if not exist "%PY_PROTO_OUT%" (
    echo ERROR: Output directory not found at %PY_PROTO_OUT%
    exit /b 1
)

echo === Step 1: Generating Python protos ===
cd /d "%GO_PROTO_DIR%"
python -m grpc_tools.protoc -I. --python_out="%PY_PROTO_OUT%" --grpc_python_out="%PY_PROTO_OUT%" engine.proto
if errorlevel 1 (
    echo ERROR: protoc failed
    exit /b 1
)
echo Generated engine_pb2.py and engine_pb2_grpc.py

echo.
echo === Step 2: Fixing imports in engine_pb2_grpc.py ===
REM The generated grpc file uses absolute import, but we need relative import
REM Change: import engine_pb2 as engine__pb2
REM To:     from . import engine_pb2 as engine__pb2

powershell -Command "(Get-Content '%PY_PROTO_OUT%\engine_pb2_grpc.py') -replace '^import engine_pb2 as', 'from . import engine_pb2 as' | Set-Content '%PY_PROTO_OUT%\engine_pb2_grpc.py'"
if errorlevel 1 (
    echo ERROR: Failed to fix imports
    exit /b 1
)
echo Fixed relative import in engine_pb2_grpc.py

echo.
echo === Step 3: Verifying generated protos ===
cd /d "%REPO_ROOT%\jeeves-airframe"

REM Verify force field exists
python -c "from jeeves_infra.protocols import engine_pb2; req = engine_pb2.InitializeSessionRequest(); has_force = hasattr(req, 'force'); print('Proto has force field:', has_force); exit(0 if has_force else 1)"
if errorlevel 1 (
    echo ERROR: Proto verification failed - force field missing
    exit /b 1
)

REM Verify gRPC imports work
python -c "from jeeves_infra.protocols import engine_pb2_grpc; print('Proto gRPC imports: OK')"
if errorlevel 1 (
    echo ERROR: Proto gRPC import verification failed
    exit /b 1
)

echo.
echo === Proto generation complete ===
exit /b 0
