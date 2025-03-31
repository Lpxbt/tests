#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data viewing script for the AvitoScraping project.
This script allows viewing the data stored in the database.
"""

import os
import sys
import json
import argparse
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

def get_metadata(conn):
    """Get metadata for all models."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT model_table_name, last_scraped, total_listings, last_status, last_error
            FROM avito_scraping.avito_scraping_metadata
            ORDER BY model_table_name
            """)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return {'columns': columns, 'rows': rows}
    except psycopg2.Error as e:
        print(f"Error getting metadata: {e}")
        return {'columns': [], 'rows': []}

def get_table_data(conn, table_name, limit=10):
    """Get data from a specific table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT id, listing_id, title, price, seller_name, seller_type, city, url,
                       date_added, last_updated
                FROM avito_scraping.{}
                ORDER BY last_updated DESC
                LIMIT %s
                """).format(sql.Identifier(table_name)),
                (limit,)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return {'columns': columns, 'rows': rows}
    except psycopg2.Error as e:
        print(f"Error getting data from avito_scraping.{table_name}: {e}")
        return {'columns': [], 'rows': []}

def get_price_stats(conn, table_name):
    """Get price statistics for a specific table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT
                    COUNT(*) as count,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price
                FROM avito_scraping.{}
                WHERE price IS NOT NULL
                """).format(sql.Identifier(table_name))
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return {'columns': columns, 'rows': rows}
    except psycopg2.Error as e:
        print(f"Error getting price stats from avito_scraping.{table_name}: {e}")
        return {'columns': [], 'rows': []}

def get_city_stats(conn, table_name, limit=5):
    """Get city statistics for a specific table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT
                    city,
                    COUNT(*) as count,
                    AVG(price) as avg_price
                FROM avito_scraping.{}
                WHERE city IS NOT NULL AND price IS NOT NULL
                GROUP BY city
                ORDER BY count DESC
                LIMIT %s
                """).format(sql.Identifier(table_name)),
                (limit,)
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return {'columns': columns, 'rows': rows}
    except psycopg2.Error as e:
        print(f"Error getting city stats from avito_scraping.{table_name}: {e}")
        return {'columns': [], 'rows': []}

def get_seller_stats(conn, table_name):
    """Get seller type statistics for a specific table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT
                    seller_type,
                    COUNT(*) as count,
                    AVG(price) as avg_price
                FROM avito_scraping.{}
                WHERE seller_type IS NOT NULL AND price IS NOT NULL
                GROUP BY seller_type
                ORDER BY count DESC
                """).format(sql.Identifier(table_name))
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return {'columns': columns, 'rows': rows}
    except psycopg2.Error as e:
        print(f"Error getting seller stats from avito_scraping.{table_name}: {e}")
        return {'columns': [], 'rows': []}

def main():
    """Main function to view the data."""
    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='View data from the AvitoScraping database.')
    parser.add_argument('--table', type=str, help='Specific table to view')
    parser.add_argument('--limit', type=int, default=10, help='Limit the number of rows to display')
    parser.add_argument('--stats', action='store_true', help='Show statistics instead of raw data')
    args = parser.parse_args()

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return

    try:
        # Load table names
        try:
            with open('data/table_names.json', 'r', encoding='utf-8') as f:
                table_names = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Get table names from metadata
            metadata = get_metadata(conn)
            if not metadata['rows']:
                print("No metadata found. Please run setup_database.py first.")
                return

            # Extract table names from metadata
            table_names = []
            model_table_name_index = metadata['columns'].index('model_table_name')
            for row in metadata['rows']:
                table_names.append(row[model_table_name_index])

        # Show metadata
        if not args.table:
            print("\n=== Scraping Metadata ===")
            metadata = get_metadata(conn)
            if metadata['rows']:
                # Print header
                print(' '.join(f'{col:<20}' for col in metadata['columns']))
                print('-' * (20 * len(metadata['columns'])))

                # Print rows
                for row in metadata['rows']:
                    formatted_row = []
                    for i, val in enumerate(row):
                        if val is None:
                            formatted_row.append('None')
                        elif isinstance(val, (int, float)):
                            formatted_row.append(str(val))
                        else:
                            formatted_row.append(str(val))
                    print(' '.join(f'{val:<20}' for val in formatted_row))
            else:
                print("No metadata found.")

            print("\nUse --table <table_name> to view data for a specific model.")
            return

        # Check if table exists
        if args.table not in table_names:
            print(f"Table {args.table} not found. Available tables:")
            for name in table_names:
                print(f"  {name}")
            return

        # Show table data or stats
        if args.stats:
            print(f"\n=== Statistics for {args.table} ===")

            # Price statistics
            print("\nPrice Statistics:")
            price_stats = get_price_stats(conn, args.table)
            if price_stats['rows']:
                # Print header
                print(' '.join(f'{col:<15}' for col in price_stats['columns']))
                print('-' * (15 * len(price_stats['columns'])))

                # Print rows
                for row in price_stats['rows']:
                    formatted_row = []
                    for i, val in enumerate(row):
                        if val is None:
                            formatted_row.append('N/A')
                        elif isinstance(val, (int, float)):
                            if price_stats['columns'][i] in ['min_price', 'max_price', 'avg_price', 'median_price']:
                                formatted_row.append(f"{int(val):,} ₽")
                            else:
                                formatted_row.append(str(val))
                        else:
                            formatted_row.append(str(val))
                    print(' '.join(f'{val:<15}' for val in formatted_row))
            else:
                print("No price statistics available.")

            # City statistics
            print("\nTop Cities:")
            city_stats = get_city_stats(conn, args.table, limit=args.limit)
            if city_stats['rows']:
                # Print header
                print(' '.join(f'{col:<20}' for col in city_stats['columns']))
                print('-' * (20 * len(city_stats['columns'])))

                # Print rows
                for row in city_stats['rows']:
                    formatted_row = []
                    for i, val in enumerate(row):
                        if val is None:
                            formatted_row.append('N/A')
                        elif isinstance(val, (int, float)):
                            if city_stats['columns'][i] == 'avg_price':
                                formatted_row.append(f"{int(val):,} ₽")
                            else:
                                formatted_row.append(str(val))
                        else:
                            formatted_row.append(str(val))
                    print(' '.join(f'{val:<20}' for val in formatted_row))
            else:
                print("No city statistics available.")

            # Seller statistics
            print("\nSeller Types:")
            seller_stats = get_seller_stats(conn, args.table)
            if seller_stats['rows']:
                # Print header
                print(' '.join(f'{col:<20}' for col in seller_stats['columns']))
                print('-' * (20 * len(seller_stats['columns'])))

                # Print rows
                for row in seller_stats['rows']:
                    formatted_row = []
                    for i, val in enumerate(row):
                        if val is None:
                            formatted_row.append('N/A')
                        elif isinstance(val, (int, float)):
                            if seller_stats['columns'][i] == 'avg_price':
                                formatted_row.append(f"{int(val):,} ₽")
                            else:
                                formatted_row.append(str(val))
                        else:
                            formatted_row.append(str(val))
                    print(' '.join(f'{val:<20}' for val in formatted_row))
            else:
                print("No seller statistics available.")
        else:
            print(f"\n=== Latest {args.limit} listings for {args.table} ===")
            data = get_table_data(conn, args.table, limit=args.limit)
            if data['rows']:
                # Get column indices for formatting
                columns = data['columns']
                price_idx = columns.index('price') if 'price' in columns else -1
                date_added_idx = columns.index('date_added') if 'date_added' in columns else -1
                last_updated_idx = columns.index('last_updated') if 'last_updated' in columns else -1
                title_idx = columns.index('title') if 'title' in columns else -1
                url_idx = columns.index('url') if 'url' in columns else -1

                # Print header
                print(' '.join(f'{col:<20}' for col in columns))
                print('-' * (20 * len(columns)))

                # Print rows
                for row in data['rows']:
                    formatted_row = list(row)

                    # Format price
                    if price_idx >= 0 and formatted_row[price_idx] is not None:
                        formatted_row[price_idx] = f"{int(formatted_row[price_idx]):,} ₽"
                    elif price_idx >= 0:
                        formatted_row[price_idx] = "N/A"

                    # Format dates
                    if date_added_idx >= 0 and formatted_row[date_added_idx] is not None:
                        formatted_row[date_added_idx] = formatted_row[date_added_idx].strftime('%Y-%m-%d %H:%M')

                    if last_updated_idx >= 0 and formatted_row[last_updated_idx] is not None:
                        formatted_row[last_updated_idx] = formatted_row[last_updated_idx].strftime('%Y-%m-%d %H:%M')

                    # Truncate long text
                    if title_idx >= 0 and formatted_row[title_idx] is not None:
                        title = formatted_row[title_idx]
                        if len(title) > 50:
                            formatted_row[title_idx] = title[:47] + '...'

                    if url_idx >= 0 and formatted_row[url_idx] is not None:
                        url = formatted_row[url_idx]
                        if len(url) > 30:
                            formatted_row[url_idx] = url[:27] + '...'

                    # Convert all values to strings
                    formatted_row = [str(val) if val is not None else "None" for val in formatted_row]

                    # Print the row
                    print(' '.join(f'{val:<20}' for val in formatted_row))
            else:
                print("No data found.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
