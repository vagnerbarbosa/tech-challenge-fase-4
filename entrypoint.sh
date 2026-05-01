#!/bin/sh
# Entrypoint script for Azure Container Instances
# Ensures environment is configured correctly

set -e

echo "========================================"
echo "Starting Tech Challenge API"
echo "========================================"
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo "Python: $(python --version)"
echo ""

# Check directory structure
echo "Contents of /app:"
ls -la /app/ 2>/dev/null || echo "Could not list /app"

echo ""
echo "Checking src module:"
if [ -d "/app/src" ]; then
    echo "OK: /app/src exists"
    ls -la /app/src/ | head -5
else
    echo "ERROR: /app/src not found!"
fi

echo ""
echo "========================================"
echo "Starting Uvicorn..."
echo "========================================"

# Run uvicorn
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips '*'
