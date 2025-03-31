"""
Script to scrape Avito.ru using the Hyperbrowser MCP server.
"""
import os
import sys
import json
import time
import random
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup

def scrape_avito_with_hyperbrowser():
    """
    Scrape Avito.ru using the Hyperbrowser MCP server.
    """
    print("Scraping Avito.ru using Hyperbrowser MCP server")
    print("==============================================")
    
    # URL to scrape
    url = "https://www.avito.ru/rossiya/gruzoviki_i_spetstehnika/gruzoviki"
    
    # Make request to Hyperbrowser MCP server
    try:
        response = requests.get(
            "http://localhost:8080/api/v1/fetch",
            params={"url": url},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            html_content = response.text
            
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all vehicle listings
            listings = soup.select('div[data-marker="item"]')
            
            if not listings:
                # Try alternative selectors
                listings = soup.select('div.item') or soup.select('div.js-catalog-item')
            
            print(f"Found {len(listings)} vehicle listings")
            
            vehicles = []
            for listing in listings:
                try:
                    # Extract basic information with fallbacks
                    title_elem = listing.select_one('h3[itemprop="name"]') or listing.select_one('h3.title') or listing.select_one('div.title')
                    price_elem = listing.select_one('span[data-marker="item-price"]') or listing.select_one('span.price') or listing.select_one('div.price')
                    url_elem = listing.select_one('a[itemprop="url"]') or listing.select_one('a.item-link') or listing.select_one('a.link')
                    
                    if not title_elem or not url_elem:
                        continue
                    
                    # Extract data
                    title = title_elem.text.strip()
                    price = price_elem.text.strip() if price_elem else "Цена не указана"
                    url = "https://www.avito.ru" + url_elem['href'] if url_elem['href'].startswith('/') else url_elem['href']
                    
                    # Create vehicle dictionary
                    vehicle = {
                        "title": title,
                        "price": price,
                        "url": url
                    }
                    
                    vehicles.append(vehicle)
                    
                except Exception as e:
                    print(f"Error parsing listing: {e}")
            
            # Save results to JSON file
            if vehicles:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"scraped_vehicles_{timestamp}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(vehicles, f, ensure_ascii=False, indent=2)
                
                print(f"Saved {len(vehicles)} vehicles to {output_file}")
            else:
                print("No vehicles found")
        else:
            print(f"Error: HTTP status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_avito_with_hyperbrowser()
