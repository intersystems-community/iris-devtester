#!/bin/bash
# Demo workflow for IRIS DevTester Container Lifecycle Commands
#
# This script demonstrates the full container lifecycle using
# iris-devtester CLI commands. It's a reference implementation
# showing best practices for container management.
#
# Usage:
#   chmod +x examples/demo-workflow.sh
#   ./examples/demo-workflow.sh

set -e  # Exit on error

echo "========================================="
echo "IRIS DevTester Container Lifecycle Demo"
echo "========================================="
echo

# Step 1: Create and start container (zero-config)
echo "Step 1: Create and start IRIS container (zero-config)"
echo "-----------------------------------------------"
echo "Command: iris-devtester container up"
echo

iris-devtester container up

echo
echo "✓ Container is running and healthy"
echo

# Step 2: Check container status
echo "Step 2: Check container status"
echo "--------------------------------"
echo "Command: iris-devtester container status"
echo

iris-devtester container status

echo

# Step 3: View container logs
echo "Step 3: View container logs (last 20 lines)"
echo "--------------------------------------------"
echo "Command: iris-devtester container logs --tail 20"
echo

iris-devtester container logs --tail 20

echo

# Step 4: Restart container
echo "Step 4: Restart container"
echo "-------------------------"
echo "Command: iris-devtester container restart"
echo

iris-devtester container restart

echo
echo "✓ Container restarted successfully"
echo

# Step 5: Check status again
echo "Step 5: Check status after restart"
echo "-----------------------------------"
echo "Command: iris-devtester container status --format json"
echo

iris-devtester container status --format json

echo

# Step 6: Stop container
echo "Step 6: Stop container gracefully"
echo "----------------------------------"
echo "Command: iris-devtester container stop"
echo

iris-devtester container stop

echo
echo "✓ Container stopped"
echo

# Step 7: Start existing container
echo "Step 7: Start existing container"
echo "---------------------------------"
echo "Command: iris-devtester container start"
echo

iris-devtester container start

echo
echo "✓ Container started from existing state"
echo

# Step 8: Cleanup (remove container)
echo "Step 8: Cleanup - remove container"
echo "-----------------------------------"
echo "Command: iris-devtester container stop && iris-devtester container remove"
echo

iris-devtester container stop
iris-devtester container remove

echo
echo "✓ Container removed (data volumes preserved)"
echo

# Summary
echo
echo "========================================="
echo "Demo Complete!"
echo "========================================="
echo
echo "What we demonstrated:"
echo "  ✓ Zero-config container creation (up)"
echo "  ✓ Status monitoring (status)"
echo "  ✓ Log viewing (logs)"
echo "  ✓ Container restart (restart)"
echo "  ✓ Graceful shutdown (stop)"
echo "  ✓ Starting existing containers (start)"
echo "  ✓ Cleanup (remove)"
echo
echo "Next steps:"
echo "  1. Try with custom config: iris-devtester container up --config iris-config.yml"
echo "  2. Use environment variables: export IRIS_SUPERSERVER_PORT=2000"
echo "  3. Enable log streaming: iris-devtester container logs --follow"
echo "  4. Check exit codes for automation: echo \$?"
echo
echo "Documentation: https://iris-devtester.readthedocs.io/"
echo
