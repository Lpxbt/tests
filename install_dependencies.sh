#!/bin/bash

# Script to install dependencies for Redis AI tools

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install basic dependencies
echo "Installing basic dependencies..."
pip install -r requirements.txt

# Install LangChain and LangGraph
echo "Installing LangChain and LangGraph..."
pip install langchain langchain-community langchain-openai langgraph

# Install Streamlit for dashboard
echo "Installing Streamlit..."
pip install streamlit

# Install additional dependencies for web scraping
echo "Installing web scraping dependencies..."
pip install aiohttp beautifulsoup4 pandas

# Install Redis dependencies
echo "Installing Redis dependencies..."
pip install redis

# Install Playwright for advanced scraping (optional)
echo "Installing Playwright (optional)..."
pip install playwright
python -m playwright install

echo "All dependencies installed successfully!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To run the dashboard, run: streamlit run dashboard.py"
