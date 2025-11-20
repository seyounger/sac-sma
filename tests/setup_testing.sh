#!/bin/bash
# Setup script for SAC-SMA testing framework

set -e  # Exit on error

# Get the repo root directory (parent of tests/)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "SAC-SMA Testing Framework Setup"
echo "Repository: $REPO_ROOT"
echo

# Check if we're in the right directory
if [ ! -f "tests/pyproject.toml" ]; then
    echo "ERROR: Must run from sac-sma root directory"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo
    echo "uv installed! Please restart your shell and run this script again."
    exit 0
fi

echo "✓ uv is installed"
echo

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo

# Activate and install dependencies
echo "Installing dependencies..."
source .venv/bin/activate
uv pip install -e tests/
echo "✓ Dependencies installed"
echo

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo
echo "To use the testing framework:"
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo
echo "  2. Run the automated tests (from repo root):"
echo "     python tests/run_branch_tests.py"
echo
echo "  3. Run pytest comparisons:"
echo "     pytest tests/ -v"
echo
echo "See tests/README.md for more details."
