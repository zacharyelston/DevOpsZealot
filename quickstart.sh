#!/bin/bash
# DevOpsZealot Quick Start Script

echo "🚀 DevOpsZealot Quick Start"
echo "=========================="

# Check Python version
echo "1. Checking Python version..."
python_version=$(python3 --version 2>&1)
if [[ $? -eq 0 ]]; then
    echo "   ✅ $python_version"
else
    echo "   ❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Docker
echo -e "\n2. Checking Docker..."
if docker info > /dev/null 2>&1; then
    docker_version=$(docker --version)
    echo "   ✅ $docker_version"
else
    echo "   ❌ Docker not running. Please start Docker Desktop"
    exit 1
fi

# Create virtual environment
echo -e "\n3. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ✅ Virtual environment already exists"
fi

# Activate virtual environment
echo -e "\n4. Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Virtual environment activated"

# Install dependencies
echo -e "\n5. Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet -e .
echo "   ✅ Dependencies installed"

# Create .env file if it doesn't exist
echo -e "\n6. Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✅ Created .env file from template"
    echo "   ⚠️  Please edit .env and add your API keys"
else
    echo "   ✅ .env file already exists"
fi

# Build Docker base image
echo -e "\n7. Building Docker base image..."
echo "   This may take a few minutes..."
if docker build -f docker/Dockerfile.base -t zealot/base:latest docker/ > /dev/null 2>&1; then
    echo "   ✅ Docker base image built"
else
    echo "   ❌ Failed to build Docker image"
fi

# Start Redis if not running
echo -e "\n8. Starting Redis..."
if docker ps | grep -q zealot-redis; then
    echo "   ✅ Redis already running"
else
    docker run -d --name zealot-redis -p 6379:6379 redis:7-alpine > /dev/null 2>&1
    echo "   ✅ Redis started"
fi

# Run setup test
echo -e "\n9. Running setup test..."
python test_setup.py

echo -e "\n=========================="
echo "✨ Setup Complete!"
echo "=========================="
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys:"
echo "   - OPENAI_API_KEY"
echo "   - GITHUB_TOKEN"
echo ""
echo "2. Start the server:"
echo "   source venv/bin/activate"
echo "   python -m zealot.server"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8090/health"
echo ""
echo "Happy autonomous coding! 🤖"
