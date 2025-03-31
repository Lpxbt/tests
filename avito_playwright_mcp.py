"""
Avito scraper using Playwright MCP server to avoid rate limiting.
"""
import os
import sys
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import re

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import tools
from utils import LLMProvider

class AvitoPlaywrightMCPScraper:
    """
    Avito scraper using Playwright MCP server to avoid rate limiting.
    """

    def __init__(self, use_llm: bool = True):
        """
        Initialize the AvitoPlaywrightMCPScraper.

        Args:
            use_llm: Whether to use LLM for data extraction and enhancement
        """
        self.use_llm = use_llm
        self.base_url = "https://www.avito.ru"
        self.search_url = f"{self.base_url}/rossiya/gruzoviki_i_spetstehnika"

        # Initialize LLM provider if needed
        self.llm_provider = None
        if self.use_llm:
            self.llm_provider = LLMProvider()

        # Categories to scrape
        self.categories = {
            "trucks": "/rossiya/gruzoviki_i_spetstehnika/gruzoviki",
            "tractors": "/rossiya/gruzoviki_i_spetstehnika/traktory",
            "buses": "/rossiya/gruzoviki_i_spetstehnika/avtobusy",
            "vans": "/rossiya/gruzoviki_i_spetstehnika/legkie_gruzoviki_do_3.5_tonn",
            "construction": "/rossiya/gruzoviki_i_spetstehnika/stroitelnaya_tehnika",
            "agricultural": "/rossiya/gruzoviki_i_spetstehnika/selhoztehnika",
            "trailers": "/rossiya/gruzoviki_i_spetstehnika/pritsepy"
        }

        # Brands to focus on
        self.target_brands = [
            "КАМАЗ", "ГАЗ", "МАЗ", "Урал", "ЗИЛ", "MAN", "Volvo", "Scania",
            "Mercedes-Benz", "DAF", "Iveco", "Renault", "Hyundai", "Isuzu"
        ]

    async def scrape_with_playwright_mcp(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a page using the Fetch MCP server.

        Args:
            url: URL to scrape

        Returns:
            Dictionary with page content and metadata or None if failed
        """
        print(f"Scraping page: {url}")

        try:
            # Make request to Fetch MCP server
            response = requests.post(
                "http://localhost:8080/api/v1/fetch",
                json={
                    "url": url,
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
                    }
                }
            )

            if response.status_code != 200:
                print(f"Error scraping page: {response.text}")
                return None

            html_content = response.text

            # Check if we're being rate limited
            if "Доступ ограничен: проблема с IP" in html_content:
                print("Warning: Access restricted due to IP issues")
                # Save HTML to file for inspection
                with open("avito_debug.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("Saved HTML to avito_debug.html for inspection")
                return None

            # Create a result dictionary similar to what the Playwright MCP server would return
            result = {
                "content": html_content,
                "url": url,
                "status": response.status_code
            }

            return result

        except Exception as e:
            print(f"Error scraping page: {e}")
            return None

    async def scrape_search_page(self, category: str, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Scrape a search page to get vehicle listings.

        Args:
            category: Category key from self.categories
            page_num: Page number

        Returns:
            List of vehicle dictionaries with basic info and URLs
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category '{category}'")

        # Build URL
        url = self.base_url + self.categories[category]

        # Add page parameter
        if page_num > 1:
            url += f"?p={page_num}"

        print(f"Scraping search page: {url}")

        # Scrape the page
        result = await self.scrape_with_playwright_mcp(url)

        if not result:
            return []

        # Parse the HTML content
        return self.parse_search_results(result["content"])

    def parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse search results page to extract vehicle listings.

        Args:
            html_content: HTML content of the search results page

        Returns:
            List of vehicle dictionaries with basic info and URLs
        """
        if not html_content:
            return []

        try:
            from bs4 import BeautifulSoup

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all vehicle listings with fallbacks
            listings = soup.select('div[data-marker="item"]')

            if not listings:
                # Try alternative selectors
                listings = soup.select('div.item') or soup.select('div.js-catalog-item') or soup.select('div.iva-item-root')

            # Print the HTML content if no listings are found (for debugging)
            if not listings:
                print("No vehicle listings found. Checking HTML structure...")
                # Save HTML to file for inspection
                with open("avito_debug.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("Saved HTML to avito_debug.html for inspection")
                return []

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
                    url = self.base_url + url_elem['href'] if url_elem['href'].startswith('/') else url_elem['href']

                    # Extract ID from URL
                    item_id = None
                    id_match = re.search(r'_(\d+)$', url)
                    if id_match:
                        item_id = id_match.group(1)

                    # Create vehicle dictionary
                    vehicle = {
                        "title": title,
                        "price": price,
                        "url": url,
                        "id": item_id
                    }

                    vehicles.append(vehicle)

                except Exception as e:
                    print(f"Error parsing listing: {e}")

            print(f"Found {len(vehicles)} vehicles in search results")
            return vehicles

        except Exception as e:
            print(f"Error parsing search results: {e}")
            return []

    async def scrape_vehicle_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a vehicle details page.

        Args:
            url: Vehicle listing URL

        Returns:
            Dictionary with vehicle details or None if failed
        """
        print(f"Scraping vehicle details: {url}")

        # Scrape the page
        result = await self.scrape_with_playwright_mcp(url)

        if not result:
            return None

        # Parse the HTML content
        return self.parse_vehicle_details(result["content"], url)

    def parse_vehicle_details(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse vehicle details page.

        Args:
            html_content: HTML content of vehicle details page
            url: Vehicle listing URL

        Returns:
            Dictionary with vehicle details or None if failed
        """
        if not html_content:
            return None

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract basic information with fallbacks
            title = soup.select_one('h1[data-marker="item-view/title"]') or soup.select_one('h1.title-info-title')
            price = soup.select_one('span[data-marker="item-view/item-price"]') or soup.select_one('span.price-value-string')
            description = soup.select_one('div[data-marker="item-view/item-description"]') or soup.select_one('div.item-description')

            # Extract parameters with fallbacks for different page structures
            params = {}

            # Try the new layout
            param_rows = soup.select('li[data-marker="item-view/item-params"]')

            if param_rows:
                for row in param_rows:
                    param_name = row.select_one('span[data-marker="item-view/item-params-label"]')
                    param_value = row.select_one('span[data-marker="item-view/item-params-value"]')

                    if param_name and param_value:
                        params[param_name.text.strip().lower()] = param_value.text.strip()
            else:
                # Try the old layout
                param_rows = soup.select('li.item-params-list-item')

                for row in param_rows:
                    param_name = row.select_one('span.item-params-label')
                    param_value = row.select_one('span.item-params-value')

                    if param_name and param_value:
                        params[param_name.text.strip().lower()] = param_value.text.strip()

            # Extract images with fallbacks
            images = []

            # Try the new layout
            image_elements = soup.select('div[data-marker="item-view/gallery"] img')

            if not image_elements:
                # Try the old layout
                image_elements = soup.select('div.gallery-img-frame img') or soup.select('div.gallery-imgs-container img')

            for img in image_elements:
                if 'src' in img.attrs:
                    # Get the highest resolution image
                    src = img['src']
                    # Replace small thumbnails with full-size images if possible
                    src = src.replace('140x105', '640x480').replace('small', 'orig')
                    images.append(src)

            # Create vehicle dictionary
            vehicle = {
                "title": title.text.strip() if title else "",
                "price": price.text.strip() if price else "",
                "description": description.text.strip() if description else "",
                "params": params,
                "images": images,
                "url": url,
                "scraped_at": datetime.now().isoformat()
            }

            # Extract common fields from params
            field_mapping = {
                "марка": "brand",
                "модель": "model",
                "год выпуска": "year",
                "пробег": "mileage",
                "тип двигателя": "engine_type",
                "мощность двигателя": "engine_power",
                "коробка передач": "transmission",
                "тип кузова": "body_type",
                "состояние": "condition",
                "владельцы": "owners",
                "vin или номер кузова": "vin"
            }

            for param_key, vehicle_key in field_mapping.items():
                if param_key in params:
                    vehicle[vehicle_key] = params[param_key]

            # Process location
            location_elem = soup.select_one('div[data-marker="item-view/item-address"]')
            if location_elem:
                vehicle["location"] = location_elem.text.strip()

            # Process seller type
            seller_elem = soup.select_one('div[data-marker="seller-info/label"]')
            if seller_elem:
                seller_text = seller_elem.text.strip().lower()
                if "компания" in seller_text or "дилер" in seller_text:
                    vehicle["seller_type"] = "dealer"
                else:
                    vehicle["seller_type"] = "private"

            # Enhance with LLM if enabled
            if self.use_llm and self.llm_provider:
                enhanced_vehicle = self.enhance_vehicle_data_with_llm(vehicle)
                if enhanced_vehicle:
                    vehicle = enhanced_vehicle

            return vehicle

        except Exception as e:
            print(f"Error parsing vehicle details: {e}")
            return None

    def enhance_vehicle_data_with_llm(self, vehicle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enhance vehicle data using LLM.

        Args:
            vehicle: Vehicle dictionary with scraped data

        Returns:
            Enhanced vehicle dictionary or None if failed
        """
        if not self.llm_provider:
            return vehicle

        try:
            # Create prompt for LLM
            prompt = f"""
            Проанализируй данные о транспортном средстве и дополни информацию, где это возможно.
            Извлеки дополнительные параметры из описания и названия.

            Данные транспортного средства:
            Название: {vehicle.get('title', '')}
            Описание: {vehicle.get('description', '')}
            Параметры: {json.dumps(vehicle.get('params', {}), ensure_ascii=False)}

            Верни только JSON с дополненными данными в следующем формате:
            {{
                "brand": "Марка автомобиля",
                "model": "Модель автомобиля",
                "year": "Год выпуска",
                "mileage": "Пробег в км (только число)",
                "engine_type": "Тип двигателя",
                "engine_power": "Мощность двигателя в л.с. (только число)",
                "transmission": "Тип коробки передач",
                "body_type": "Тип кузова",
                "condition": "Состояние",
                "category": "Категория транспорта",
                "additional_info": "Дополнительная важная информация"
            }}
            """

            # Get response from LLM
            response = self.llm_provider.generate(prompt)

            # Parse JSON response
            try:
                # Extract JSON from response (it might be wrapped in markdown code blocks)
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response

                enhanced_data = json.loads(json_str)

                # Update vehicle with enhanced data
                for key, value in enhanced_data.items():
                    if value and (key not in vehicle or not vehicle[key]):
                        vehicle[key] = value

                return vehicle
            except json.JSONDecodeError as e:
                print(f"Error parsing LLM response as JSON: {e}")
                return vehicle

        except Exception as e:
            print(f"Error enhancing vehicle data with LLM: {e}")
            return vehicle

    async def scrape_category(self, category: str, max_pages: int = 5, max_vehicles: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape vehicles from a specific category.

        Args:
            category: Category key from self.categories
            max_pages: Maximum number of pages to scrape
            max_vehicles: Maximum number of vehicles to scrape

        Returns:
            List of vehicle dictionaries with detailed information
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category '{category}'")

        all_vehicles = []
        page_num = 1

        while page_num <= max_pages and len(all_vehicles) < max_vehicles:
            # Long delay before starting a new page to avoid rate limiting
            await asyncio.sleep(5 + random.random() * 10)  # 5-15 seconds delay

            print(f"Scraping page {page_num} of category '{category}'...")

            # Scrape search page
            vehicles = await self.scrape_search_page(category, page_num)

            if not vehicles:
                print("No vehicles found on this page. Moving to next category.")
                break

            print(f"Found {len(vehicles)} vehicles on page {page_num}. Processing...")

            # Process only a subset of vehicles per page to avoid detection
            # This is more like human behavior - not clicking on every single listing
            vehicles_to_process = min(len(vehicles), 3)  # Process max 3 vehicles per page
            selected_vehicles = random.sample(vehicles, vehicles_to_process)

            # Get details for selected vehicles
            for i, vehicle in enumerate(selected_vehicles):
                if len(all_vehicles) >= max_vehicles:
                    break

                print(f"Processing vehicle {i+1}/{vehicles_to_process} on page {page_num}...")

                # Longer delay between vehicle details to mimic reading the page
                await asyncio.sleep(3 + random.random() * 7)  # 3-10 seconds delay

                # Get vehicle details
                vehicle_details = await self.scrape_vehicle_details(vehicle["url"])
                if vehicle_details:
                    all_vehicles.append(vehicle_details)
                    print(f"Added vehicle: {vehicle_details.get('title', 'Unknown')}")

                # Random delay between requests - much longer to avoid detection
                await asyncio.sleep(5 + random.random() * 10)  # 5-15 seconds delay

            # Go to next page
            page_num += 1

            # Random delay between pages - very long to avoid detection
            await asyncio.sleep(10 + random.random() * 10)  # 10-20 seconds delay

        print(f"Scraped {len(all_vehicles)} vehicles from category '{category}'")
        return all_vehicles

    async def scrape_all_categories(self, max_pages_per_category: int = 3, max_vehicles_per_category: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape vehicles from all categories.

        Args:
            max_pages_per_category: Maximum number of pages to scrape per category
            max_vehicles_per_category: Maximum number of vehicles to scrape per category

        Returns:
            Dictionary mapping category names to lists of vehicle dictionaries
        """
        results = {}

        for category in self.categories:
            print(f"Scraping category: {category}")
            vehicles = await self.scrape_category(category, max_pages_per_category, max_vehicles_per_category)
            results[category] = vehicles

            # Random delay between categories
            await asyncio.sleep(10 + random.random() * 10)

        return results

    def save_to_json(self, vehicles: Union[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]], file_path: str) -> bool:
        """
        Save scraped vehicles to a JSON file.

        Args:
            vehicles: List of vehicle dictionaries or dictionary mapping categories to vehicle lists
            file_path: Path to save the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(vehicles, f, ensure_ascii=False, indent=2)

            print(f"Saved vehicles to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving vehicles to JSON: {e}")
            return False

    def save_to_csv(self, vehicles: List[Dict[str, Any]], file_path: str) -> bool:
        """
        Save scraped vehicles to a CSV file.

        Args:
            vehicles: List of vehicle dictionaries
            file_path: Path to save the CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd

            # Flatten nested dictionaries
            flattened_vehicles = []

            for vehicle in vehicles:
                flat_vehicle = {}

                # Copy top-level fields
                for key, value in vehicle.items():
                    if key != 'params' and key != 'images' and not isinstance(value, (dict, list)):
                        flat_vehicle[key] = value

                # Copy params
                if 'params' in vehicle and isinstance(vehicle['params'], dict):
                    for param_key, param_value in vehicle['params'].items():
                        flat_vehicle[f"param_{param_key}"] = param_value

                # Handle images
                if 'images' in vehicle and isinstance(vehicle['images'], list):
                    for i, img_url in enumerate(vehicle['images'][:5]):  # Limit to first 5 images
                        flat_vehicle[f"image_{i+1}"] = img_url

                flattened_vehicles.append(flat_vehicle)

            # Create DataFrame and save to CSV
            df = pd.DataFrame(flattened_vehicles)
            df.to_csv(file_path, index=False, encoding='utf-8')

            print(f"Saved vehicles to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving vehicles to CSV: {e}")
            return False

async def main_async():
    """Async main function."""
    print("AvitoPlaywrightMCPScraper - Using Playwright MCP Server")
    print("===================================================")
    print("This version uses the Playwright MCP server to avoid detection")
    print("It will scrape very slowly to avoid IP bans")
    print()

    # Initialize scraper
    scraper = AvitoPlaywrightMCPScraper(use_llm=True)

    # Scrape a single category as a test with very conservative limits
    print("Starting scraping with conservative limits...")
    print("This will take some time due to intentional delays")
    print()

    # Use very conservative limits - just 1 page and 2 vehicles
    # This is to demonstrate the functionality without risking IP ban
    vehicles = await scraper.scrape_category("trucks", max_pages=1, max_vehicles=2)

    # Save results
    if vehicles:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"scraped_vehicles_{timestamp}.json"
        csv_file = f"scraped_vehicles_{timestamp}.csv"

        scraper.save_to_json(vehicles, json_file)
        scraper.save_to_csv(vehicles, csv_file)

        print(f"\nSaved {len(vehicles)} vehicles to:")
        print(f"- JSON: {json_file}")
        print(f"- CSV: {csv_file}")
    else:
        print("\nNo vehicles were scraped. This could be due to:")
        print("- Rate limiting by Avito")
        print("- Changes in Avito's website structure")
        print("- Network issues")

    print("\nScraping completed!")
    print("To scrape more vehicles, adjust the max_pages and max_vehicles parameters")
    print("Remember to keep the limits conservative to avoid IP bans")

def main():
    """Main function."""
    # Run async main
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
