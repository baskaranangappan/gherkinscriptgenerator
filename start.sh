#!/bin/bash
# BDD Test Generator - Linux/Mac Startup Script

set -e

echo "========================================"
echo "BDD Test Generator - Starting..."
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" &> /dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to install dependencies"
        exit 1
    fi
    
    echo "🌐 Installing Playwright browsers..."
    playwright install chromium
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found"
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
        echo ""
        echo "Please edit .env file and add your API keys:"
        echo "  nano .env"
        echo ""
        echo "Then run this script again:"
        echo "  ./start.sh"
        exit 1
    else
        echo "❌ ERROR: .env.example not found"
        exit 1
    fi
fi

# Start the application
echo ""
echo "🚀 Starting BDD Test Generator..."
echo ""
python start.py
