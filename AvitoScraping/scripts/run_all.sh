#!/bin/bash

# Run all script
# This script runs the entire process from research to scraping

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Create data directory if it doesn't exist
mkdir -p data

echo "=== AvitoScraping - Run All ==="
echo "Starting at $(date)"
echo

# Step 1: Research models
echo "Step 1: Researching top commercial transport models..."
python3 src/research_models.py
if [ $? -ne 0 ]; then
    echo "Error: Research failed."
    exit 1
fi
echo

# Step 2: Organize database structure
echo "Step 2: Organizing database structure..."
./scripts/organize_db.sh
if [ $? -ne 0 ]; then
    echo "Error: Database organization failed."
    exit 1
fi
echo

# Step 3: Setup database tables
echo "Step 3: Setting up database tables..."
python3 src/setup_database.py
if [ $? -ne 0 ]; then
    echo "Error: Database setup failed."
    exit 1
fi
echo

# Step 4: Scrape data
echo "Step 4: Scraping data from Avito.ru..."
python3 src/scrape_avito.py
if [ $? -ne 0 ]; then
    echo "Error: Scraping failed."
    exit 1
fi
echo

# Step 5: View data
echo "Step 5: Viewing data summary..."
python3 src/view_data.py
echo

echo "All steps completed successfully at $(date)"
echo "To set up daily updates, run: ./scripts/setup_daily_updates.sh"
