#!/bin/bash

# Wrapper script to run the update_database.py script with the virtual environment
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Create logs directory if it doesn't exist
mkdir -p "data/logs"

# Activate virtual environment and run the update script
source venv/bin/activate
python src/update_database.py --now >> data/logs/update_$(date +%Y%m%d).log 2>&1
