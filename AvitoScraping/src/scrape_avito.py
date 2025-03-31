#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Avito.ru scraper for commercial transport listings.
This script scrapes listings for the top commercial transport models and stores them in the database.
"""

import os
import sys
import json
import time
import random
import re
from datetime import datetime
import psycopg2
from psycopg2 import sql
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from dotenv import load_dotenv
from tqdm import tqdm
from retry import retry

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Constants
BASE_URL = "https://www.avito.ru"
TRANSPORT_URL = f"{BASE_URL}/rossiya/gruzoviki_i_spetstehnika"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

# Initialize user agent rotator
ua = UserAgent()

def get_db_connection():
    """Get a connection to the database."""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.autocommit = True
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

def get_random_delay():
    """Get a random delay between requests to avoid being blocked."""
    base_delay = float(os.getenv("SCRAPING_DELAY", "2"))
    return base_delay + random.uniform(0, 1)

def update_metadata(conn, table_name, status, error=None, total_listings=None):
    """Update the metadata table with the scraping status."""
    try:
        with conn.cursor() as cur:
            query = """
            UPDATE avito_scraping.avito_scraping_metadata
            SET last_scraped = NOW(),
                last_status = %s,
                last_error = %s,
                updated_at = NOW()
            """
            params = [status, error]

            if total_listings is not None:
                query += ", total_listings = %s"
                params.append(total_listings)

            query += " WHERE model_table_name = %s"
            params.append(table_name)

            cur.execute(query, params)
    except psycopg2.Error as e:
        print(f"Error updating metadata for {table_name}: {e}")

@retry(tries=3, delay=2, backoff=2)
def fetch_page(url):
    """Fetch a page with retry logic."""
    headers = HEADERS.copy()
    headers["User-Agent"] = ua.random

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def parse_price(price_text):
    """Parse the price from the text."""
    if not price_text or price_text.lower() == "цена не указана":
        return None

    # Extract digits
    digits = re.findall(r'\d+', price_text.replace(' ', ''))
    if digits:
        return int(''.join(digits))
    return None

def parse_seller_type(seller_text):
    """Parse the seller type from the text."""
    if not seller_text:
        return "unknown"

    seller_text = seller_text.lower()
    if "компания" in seller_text or "автосалон" in seller_text or "дилер" in seller_text:
        return "dealer"
    elif "частное лицо" in seller_text:
        return "private"
    else:
        return "unknown"

def search_model(search_term):
    """Search for a specific model on Avito."""
    encoded_term = requests.utils.quote(search_term)
    search_url = f"{TRANSPORT_URL}?q={encoded_term}"

    try:
        html = fetch_page(search_url)
        soup = BeautifulSoup(html, 'lxml')

        # Find all listing items
        listings = []
        items = soup.select('div[data-marker="item"]')

        for item in items:
            try:
                # Extract listing ID
                listing_id = item.get('data-item-id')

                # Extract title
                title_elem = item.select_one('[itemprop="name"]')
                title = title_elem.text.strip() if title_elem else "Unknown Title"

                # Extract URL
                url_elem = item.select_one('a[itemprop="url"]')
                url = BASE_URL + url_elem['href'] if url_elem else None

                # Extract price
                price_elem = item.select_one('[itemprop="price"]')
                price_text = price_elem.text.strip() if price_elem else None
                price = parse_price(price_text)

                # Extract seller
                seller_elem = item.select_one('.styles-module-noAccent-nZxz7')
                seller_name = seller_elem.text.strip() if seller_elem else None
                seller_type = parse_seller_type(seller_name)

                # Extract city
                city_elem = item.select_one('[data-marker="item-address"]')
                city = city_elem.text.strip() if city_elem else None

                # Create listing object
                listing = {
                    'listing_id': listing_id,
                    'title': title,
                    'price': price,
                    'seller_name': seller_name,
                    'seller_type': seller_type,
                    'city': city,
                    'url': url
                }

                listings.append(listing)
            except Exception as e:
                print(f"Error parsing listing: {e}")
                continue

        return listings
    except Exception as e:
        print(f"Error searching for {search_term}: {e}")
        return []

def get_listing_details(url):
    """Get detailed information about a listing."""
    try:
        html = fetch_page(url)
        soup = BeautifulSoup(html, 'lxml')

        # Extract description
        description_elem = soup.select_one('[itemprop="description"]')
        description = description_elem.text.strip() if description_elem else None

        return {'description': description}
    except Exception as e:
        print(f"Error getting details for {url}: {e}")
        return {'description': None}

def save_listing(conn, table_name, listing):
    """Save a listing to the database."""
    try:
        with conn.cursor() as cur:
            # Check if listing exists
            cur.execute(
                sql.SQL("SELECT 1 FROM avito_scraping.{} WHERE listing_id = %s").format(sql.Identifier(table_name)),
                (listing['listing_id'],)
            )

            if cur.fetchone() is None:
                # Insert new listing
                cur.execute(
                    sql.SQL("""
                    INSERT INTO avito_scraping.{}
                    (listing_id, title, price, seller_name, seller_type, city, url, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """).format(sql.Identifier(table_name)),
                    (
                        listing['listing_id'],
                        listing['title'],
                        listing['price'],
                        listing['seller_name'],
                        listing['seller_type'],
                        listing['city'],
                        listing['url'],
                        listing.get('description')
                    )
                )
                return "inserted"
            else:
                # Update existing listing
                cur.execute(
                    sql.SQL("""
                    UPDATE avito_scraping.{}
                    SET title = %s, price = %s, seller_name = %s, seller_type = %s,
                        city = %s, description = %s, last_updated = NOW()
                    WHERE listing_id = %s
                    """).format(sql.Identifier(table_name)),
                    (
                        listing['title'],
                        listing['price'],
                        listing['seller_name'],
                        listing['seller_type'],
                        listing['city'],
                        listing.get('description'),
                        listing['listing_id']
                    )
                )
                return "updated"
    except psycopg2.Error as e:
        print(f"Error saving listing {listing['listing_id']} to avito_scraping.{table_name}: {e}")
        return "error"

def scrape_model(conn, model):
    """Scrape listings for a specific model."""
    table_name = model['table_name']
    search_terms = model['search_terms']

    print(f"\nScraping {model['make']} {model['model']} (Table: {table_name})")

    # Update metadata to indicate scraping has started
    update_metadata(conn, table_name, "scraping")

    all_listings = []

    # Search for each term
    for term in search_terms:
        print(f"  Searching for: {term}")
        listings = search_model(term)
        print(f"  Found {len(listings)} listings")
        all_listings.extend(listings)

        # Random delay between searches
        time.sleep(get_random_delay())

    # Remove duplicates based on listing_id
    unique_listings = {listing['listing_id']: listing for listing in all_listings}.values()
    print(f"  Total unique listings: {len(unique_listings)}")

    # Get details for each listing and save to database
    inserted = 0
    updated = 0
    errors = 0

    for listing in tqdm(unique_listings, desc="Processing listings", unit="listing"):
        try:
            # Get detailed information if URL is available
            if listing['url']:
                details = get_listing_details(listing['url'])
                listing.update(details)

                # Random delay between requests
                time.sleep(get_random_delay())

            # Save to database
            result = save_listing(conn, table_name, listing)

            if result == "inserted":
                inserted += 1
            elif result == "updated":
                updated += 1
            else:
                errors += 1
        except Exception as e:
            print(f"Error processing listing {listing.get('listing_id')}: {e}")
            errors += 1

    # Update metadata
    total_listings = len(unique_listings)
    status = "completed" if errors == 0 else "completed_with_errors"
    error_msg = f"{errors} errors occurred" if errors > 0 else None
    update_metadata(conn, table_name, status, error_msg, total_listings)

    print(f"  Results: {inserted} inserted, {updated} updated, {errors} errors")
    return inserted, updated, errors

def main():
    """Main function to run the scraping process."""
    print("Starting Avito.ru scraping process...")

    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load model data
    try:
        with open('data/top_commercial_models.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        models = data['models']
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading model data: {e}")
        print("Please run research_models.py first to generate the model data.")
        return

    # Connect to the database
    conn = get_db_connection()
    if not conn:
        return

    try:
        # Scrape each model
        total_inserted = 0
        total_updated = 0
        total_errors = 0

        for model in models:
            inserted, updated, errors = scrape_model(conn, model)
            total_inserted += inserted
            total_updated += updated
            total_errors += errors

        print("\nScraping process completed.")
        print(f"Total results: {total_inserted} inserted, {total_updated} updated, {total_errors} errors")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
