#!/bin/bash
# ============================================================================
# EDP-IO - Developer Setup Script
# ============================================================================
# Installs pre-commit hooks to prevent formatting issues
#
# USAGE:
#   bash setup_dev.sh       # Install hooks
#   pre-commit run --all    # Test hooks
#   pre-commit uninstall    # Remove hooks
# ============================================================================

set -e

echo "🚀 Setting up EDP-IO development environment..."

# 1. Check Python version
echo "📦 Checking Python version..."
python --version

# 2. Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# 3. Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate || . .venv/Scripts/activate

# 4. Install pre-commit
echo "📦 Installing pre-commit..."
pip install --upgrade pip
pip install pre-commit

# 5. Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# 6. Install project dependencies
echo "📦 Installing project dependencies..."
pip install -r requirements.txt

# 7. Install development dependencies
echo "📦 Installing development dependencies..."
pip install black flake8 mypy isort bandit pytest pytest-cov

# 8. Run pre-commit on all files (first time)
echo "✅ Running pre-commit on all files (first time)..."
pre-commit run --all-files || true  # Don't fail on first run

echo ""
echo "✨ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Review any formatting changes"
echo "   2. Commit the changes: git commit -m 'chore: run pre-commit on all files'"
echo "   3. Push: git push origin main"
echo ""
echo "🪝 Pre-commit hooks are now active:"
echo "   - Black will format code before commit"
echo "   - isort will sort imports"
echo "   - flake8 will lint code"
echo "   - Bandit will check for security issues"
echo ""
echo "To temporarily skip hooks, use: git commit --no-verify"
