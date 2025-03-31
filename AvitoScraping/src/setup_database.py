#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database setup script for the AvitoScraping project.
This script creates the necessary tables in the Neon PostgreSQL database.
"""

import os
import sys
import json
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get a connection to the database."""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

def create_table(conn, table_name):
    """Create a table for a specific model."""
    try:
        with conn.cursor() as cur:
            # Create avito_scraping schema if it doesn't exist
            cur.execute("CREATE SCHEMA IF NOT EXISTS avito_scraping")

            # Check if table exists in avito_scraping schema
            cur.execute(
                sql.SQL("SELECT to_regclass(%s)").format(),
                (f"avito_scraping.{table_name}",)
            )
            if cur.fetchone()[0] is not None:
                print(f"Table avito_scraping.{table_name} already exists.")
                return True

            # Create the table in avito_scraping schema
            cur.execute(
                sql.SQL("""
                CREATE TABLE IF NOT EXISTS avito_scraping.{} (
                    id SERIAL PRIMARY KEY,
                    listing_id VARCHAR(255) UNIQUE,
                    title TEXT NOT NULL,
                    price INTEGER,
                    seller_name TEXT,
                    seller_type VARCHAR(50),
                    city TEXT,
                    url TEXT,
                    description TEXT,
                    date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """).format(sql.Identifier(table_name))
            )

            # Create index on listing_id
            index_name = f"{table_name}_listing_id_idx"
            cur.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON avito_scraping.{} (listing_id)")
                .format(sql.Identifier(index_name), sql.Identifier(table_name))
            )

            print(f"Created table avito_scraping.{table_name}")
            return True
    except psycopg2.Error as e:
        print(f"Error creating table avito_scraping.{table_name}: {e}")
        return False

def create_metadata_table(conn):
    """Create a metadata table to track scraping status."""
    try:
        with conn.cursor() as cur:
            # Create avito_scraping schema if it doesn't exist
            cur.execute("CREATE SCHEMA IF NOT EXISTS avito_scraping")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS avito_scraping.avito_scraping_metadata (
                id SERIAL PRIMARY KEY,
                model_table_name VARCHAR(255) UNIQUE,
                last_scraped TIMESTAMP WITH TIME ZONE,
                total_listings INTEGER DEFAULT 0,
                last_status VARCHAR(50),
                last_error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """)
            print("Created metadata table avito_scraping.avito_scraping_metadata")
            return True
    except psycopg2.Error as e:
        print(f"Error creating metadata table: {e}")
        return False

def initialize_metadata(conn, table_names):
    """Initialize the metadata table with the model table names."""
    try:
        with conn.cursor() as cur:
            for table_name in table_names:
                # Check if entry exists
                cur.execute(
                    "SELECT 1 FROM avito_scraping.avito_scraping_metadata WHERE model_table_name = %s",
                    (table_name,)
                )
                if cur.fetchone() is None:
                    # Insert new entry
                    cur.execute(
                        """
                        INSERT INTO avito_scraping.avito_scraping_metadata
                        (model_table_name, last_status)
                        VALUES (%s, 'initialized')
                        """,
                        (table_name,)
                    )
                    print(f"Initialized metadata for {table_name}")
            return True
    except psycopg2.Error as e:
        print(f"Error initializing metadata: {e}")
        return False

def main():
    """Main function to set up the database."""
    print("Starting database setup...")

    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load table names
    try:
        with open('data/table_names.json', 'r', encoding='utf-8') as f:
            table_names = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading table names: {e}")
        print("Please run research_models.py first to generate the table names.")
        return

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return

    try:
        # Create metadata table
        if not create_metadata_table(conn):
            return

        # Create tables for each model
        success_count = 0
        for table_name in table_names:
            if create_table(conn, table_name):
                success_count += 1

        # Initialize metadata
        if not initialize_metadata(conn, table_names):
            return

        print(f"\nDatabase setup completed. Created {success_count}/{len(table_names)} tables.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
