#!/bin/bash

echo "=== Testing Reusable Policies Feature ==="
echo ""

echo "1. Check if DockFlare is running..."
if docker ps | grep -q dockflare; then
    echo "✓ DockFlare is running"
else
    echo "✗ DockFlare is not running"
    exit 1
fi

echo ""
echo "2. Check logs for reusable policies module..."
docker logs dockflare 2>&1 | grep -i "reusable" || echo "No reusable policy logs yet"

echo ""
echo "3. Check config flag..."
docker exec dockflare python3 -c "from app import config; print(f'USE_REUSABLE_POLICIES: {config.USE_REUSABLE_POLICIES}')" 2>/dev/null || echo "Could not check config"

echo ""
echo "4. Test import of reusable_policies module..."
docker exec dockflare python3 -c "from app.core import reusable_policies; print('✓ Module imported successfully')" 2>/dev/null || echo "✗ Module import failed"

echo ""
echo "5. Check if feature is active in access_manager..."
docker exec dockflare python3 -c "
from app import config
from app.core import access_manager
import inspect

source = inspect.getsource(access_manager.handle_access_policy_from_labels)
if 'reusable_policies' in source:
    print('✓ Reusable policies integrated in access_manager')
else:
    print('✗ Reusable policies not found in access_manager')
" 2>/dev/null || echo "Could not check integration"

echo ""
echo "=== Test Complete ==="
