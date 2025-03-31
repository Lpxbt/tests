#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Research script to identify and process top commercial transport models in Russia.
This script loads the pre-researched data and prepares it for the scraping process.
"""

import json
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_top_models():
    """Load the top commercial transport models from the JSON file."""
    try:
        with open('data/top_commercial_models.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data['models'])} models from research data.")
        print(f"Last updated: {data['last_updated']}")
        return data
    except FileNotFoundError:
        print("Error: top_commercial_models.json not found.")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in top_commercial_models.json.")
        return None

def display_models(data):
    """Display the models in a tabular format."""
    if not data:
        return

    models = data['models']

    print("\nTop Commercial Transport Models in Russia:")
    print(f"{'ID':<4} {'Make':<15} {'Model':<15} {'Type':<25} {'Table Name':<20}")
    print("-" * 80)

    for model in models:
        print(f"{model['id']:<4} {model['make']:<15} {model['model']:<15} {model['type']:<25} {model['table_name']:<20}")

    # Count by type
    type_counts = {}
    for model in models:
        model_type = model['type']
        type_counts[model_type] = type_counts.get(model_type, 0) + 1

    print("\nBreakdown by Type:")
    print(f"{'Type':<25} {'Count':<5}")
    print("-" * 30)
    for model_type, count in type_counts.items():
        print(f"{model_type:<25} {count:<5}")

    # Count by make
    make_counts = {}
    for model in models:
        make = model['make']
        make_counts[make] = make_counts.get(make, 0) + 1

    print("\nBreakdown by Make:")
    print(f"{'Make':<15} {'Count':<5}")
    print("-" * 20)
    for make, count in sorted(make_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{make:<15} {count:<5}")

def export_search_terms(data):
    """Export search terms for each model to individual files."""
    if not data:
        return

    os.makedirs('data/search_terms', exist_ok=True)

    for model in data['models']:
        filename = f"data/search_terms/{model['table_name']}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for term in model['search_terms']:
                f.write(f"{term}\n")
        print(f"Exported search terms for {model['make']} {model['model']} to {filename}")

def main():
    """Main function to run the research process."""
    print("Starting research process...")

    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load and display the top models
    data = load_top_models()
    if data:
        display_models(data)
        export_search_terms(data)

        # Export the list of table names for the database setup
        table_names = [model['table_name'] for model in data['models']]
        with open('data/table_names.json', 'w', encoding='utf-8') as f:
            json.dump(table_names, f, ensure_ascii=False, indent=2)
        print(f"\nExported {len(table_names)} table names to data/table_names.json")

        print("\nResearch process completed successfully.")
    else:
        print("Research process failed.")

if __name__ == "__main__":
    main()
