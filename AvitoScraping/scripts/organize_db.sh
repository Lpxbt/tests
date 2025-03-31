#!/bin/bash

# Script to organize the Neon database structure
# Creates schemas for "Knowledge DB" and "Avito Scraping"
# Moves tables to their respective schemas

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "Loaded environment variables from .env"
else
    echo "Warning: .env file not found. Make sure DATABASE_URL is set."
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL is not set. Please set it in the .env file or as an environment variable."
    exit 1
fi

echo "=== Organizing Neon Database Structure ==="
echo "This script will create schemas for 'Knowledge DB' and 'Avito Scraping'"
echo "and move tables to their respective schemas."
echo

# Execute the SQL script
echo "Executing SQL script..."
psql "$DATABASE_URL" -f sql/organize_database.sql

# Check if the execution was successful
if [ $? -eq 0 ]; then
    echo "Database organization completed successfully."
    
    # List the schemas and tables
    echo
    echo "=== Database Structure ==="
    psql "$DATABASE_URL" -c "SELECT * FROM public.database_structure ORDER BY schema_name, table_name;"
else
    echo "Error: Failed to execute the SQL script."
    exit 1
fi

echo
echo "The database has been organized with the following structure:"
echo "1. knowledge_db schema: Contains tables for the Business Trucks knowledge base"
echo "2. avito_scraping schema: Contains tables for the Avito Scraping project"
echo "3. public schema: Contains the database_structure view"
echo
echo "You can view the database structure at any time with:"
echo "psql \"$DATABASE_URL\" -c \"SELECT * FROM public.database_structure ORDER BY schema_name, table_name;\""
