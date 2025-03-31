"""
AvitoScraping Agent - Intelligent scraper for Avito.ru commercial vehicles.
"""
import os
import sys
import json
import time
import random
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re
import urllib.parse

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import tools
from utils import LLMProvider
from redis_connection import get_redis_client
from vector_search.vector_store import VectorStore

# Try to import required libraries
try:
    import aiohttp
    from bs4 import BeautifulSoup
    import pandas as pd
    SCRAPING_LIBS_AVAILABLE = True
except ImportError:
    SCRAPING_LIBS_AVAILABLE = False
    print("Warning: Scraping libraries not available. Install with:")
    print("pip install aiohttp beautifulsoup4 pandas")

class AvitoScrapingAgent:
    """
    Intelligent agent for scraping commercial vehicle data from Avito.ru.
    """

    def __init__(self, use_llm: bool = True, use_proxy: bool = False):
        """
        Initialize the AvitoScrapingAgent.

        Args:
            use_llm: Whether to use LLM for data extraction and enhancement
            use_proxy: Whether to use proxy server for requests
        """
        self.use_llm = use_llm
        self.use_proxy = use_proxy
        self.base_url = "https://www.avito.ru"
        self.search_url = f"{self.base_url}/rossiya/gruzoviki_i_spetstehnika"

        # Initialize LLM provider if needed
        self.llm_provider = None
        if self.use_llm:
            self.llm_provider = LLMProvider()

        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]

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

    async def get_random_proxy(self) -> Optional[str]:
        """
        Get a random proxy from a proxy service.
        Uses MCP proxy server if available.

        Returns:
            Proxy string or None
        """
        # For demo purposes, we'll just return None and rely on other anti-rate-limiting techniques
        # In a real implementation, you would connect to the MCP proxy server
        return None

    async def make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Make an HTTP request with error handling and retries.

        Args:
            url: URL to request
            headers: Optional headers

        Returns:
            HTML content or None if failed
        """
        if not SCRAPING_LIBS_AVAILABLE:
            print("Error: Scraping libraries not available.")
            return None

        # Default headers
        if headers is None:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": self.base_url,
                "Connection": "keep-alive"
            }

        # Get proxy
        proxy = await self.get_random_proxy()

        # Maximum retries
        max_retries = 5  # Increased from 3 to 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Add random delay before request to avoid rate limiting
                await asyncio.sleep(2 + random.random() * 8)  # Random delay between 2-10 seconds

                # Rotate user agent for each request
                if headers is None:
                    headers = {}
                headers["User-Agent"] = random.choice(self.user_agents)

                # Add additional headers to mimic a real browser
                headers.update({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "max-age=0",
                    "TE": "Trailers"
                })

                # Add a referer to make the request look more legitimate
                if "Referer" not in headers:
                    headers["Referer"] = self.base_url

                # Create a session with cookies enabled
                async with aiohttp.ClientSession(cookies=aiohttp.CookieJar()) as session:
                    async with session.get(
                        url,
                        headers=headers,
                        proxy=proxy,
                        timeout=30,
                        allow_redirects=True
                    ) as response:
                        if response.status == 200:
                            # Success - return the response text
                            return await response.text()
                        elif response.status == 403 or response.status == 429:
                            # Rate limited - wait longer before retry
                            print(f"Rate limited (status {response.status}). Waiting before retry...")
                            # Exponential backoff
                            wait_time = 15 * (2 ** retry_count) + random.random() * 10
                            print(f"Waiting {wait_time:.2f} seconds before retry {retry_count + 1}/{max_retries}")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"Error: HTTP status {response.status} for URL: {url}")

            except aiohttp.ClientError as e:
                print(f"Request error: {e}")
            except asyncio.TimeoutError:
                print(f"Request timeout for URL: {url}")

            # Increment retry count and wait before retrying
            retry_count += 1

            # Exponential backoff for retries
            wait_time = 5 * (2 ** retry_count) + random.random() * 5
            print(f"Retry {retry_count}/{max_retries} in {wait_time:.2f} seconds...")
            await asyncio.sleep(wait_time)

        print(f"Failed to retrieve URL after {max_retries} attempts: {url}")
        return None

    async def search_vehicles(self, category: str, page: int = 1, params: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Search for vehicles in a specific category.

        Args:
            category: Category key from self.categories
            page: Page number
            params: Additional search parameters

        Returns:
            HTML content of search results or None if failed
        """
        if category not in self.categories:
            print(f"Error: Unknown category '{category}'")
            return None

        # Build URL
        url = self.base_url + self.categories[category]

        # Add page parameter
        if page > 1:
            url += f"?p={page}"

        # Add additional parameters
        if params:
            separator = "&" if "?" in url else "?"
            param_str = urllib.parse.urlencode(params)
            url += f"{separator}{param_str}"

        print(f"Searching vehicles in category '{category}', page {page}...")
        return await self.make_request(url)

    def parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse search results page to extract vehicle listings.

        Args:
            html_content: HTML content of search results page

        Returns:
            List of vehicle dictionaries with basic info and URLs
        """
        if not html_content:
            return []

        vehicles = []
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all vehicle listings
        # Note: This selector needs to be updated based on Avito's actual HTML structure
        listings = soup.select('div[data-marker="item"]')

        for listing in listings:
            try:
                # Extract basic information
                title_elem = listing.select_one('h3[itemprop="name"]')
                price_elem = listing.select_one('span[data-marker="item-price"]')
                url_elem = listing.select_one('a[itemprop="url"]')

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

    async def get_vehicle_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a vehicle.

        Args:
            url: Vehicle listing URL

        Returns:
            Dictionary with vehicle details or None if failed
        """
        print(f"Getting details for vehicle: {url}")

        # Make request to vehicle page
        html_content = await self.make_request(url)
        if not html_content:
            return None

        # Parse vehicle details
        return self.parse_vehicle_details(html_content, url)

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
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract basic information
            title = soup.select_one('h1[data-marker="item-view/title"]')
            price = soup.select_one('span[data-marker="item-view/item-price"]')
            description = soup.select_one('div[data-marker="item-view/item-description"]')

            # Extract parameters
            params = {}
            param_rows = soup.select('li[data-marker="item-view/item-params"]')

            for row in param_rows:
                param_name = row.select_one('span[data-marker="item-view/item-params-label"]')
                param_value = row.select_one('span[data-marker="item-view/item-params-value"]')

                if param_name and param_value:
                    params[param_name.text.strip().lower()] = param_value.text.strip()

            # Extract images
            images = []
            image_elements = soup.select('div[data-marker="item-view/gallery"] img')

            for img in image_elements:
                if 'src' in img.attrs:
                    images.append(img['src'])

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
        all_vehicles = []
        page = 1

        while page <= max_pages and len(all_vehicles) < max_vehicles:
            # Search for vehicles
            html_content = await self.search_vehicles(category, page)
            if not html_content:
                break

            # Parse search results
            vehicles = self.parse_search_results(html_content)
            if not vehicles:
                break

            # Get details for each vehicle
            for vehicle in vehicles:
                if len(all_vehicles) >= max_vehicles:
                    break

                # Get vehicle details
                vehicle_details = await self.get_vehicle_details(vehicle["url"])
                if vehicle_details:
                    all_vehicles.append(vehicle_details)

                # Random delay between requests
                await asyncio.sleep(2 + random.random() * 3)

            # Go to next page
            page += 1

            # Random delay between pages
            await asyncio.sleep(5 + random.random() * 5)

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
        if not SCRAPING_LIBS_AVAILABLE:
            print("Error: pandas not available for CSV export.")
            return False

        try:
            # Flatten nested dictionaries
            flattened_vehicles = []

            for vehicle in vehicles:
                flat_vehicle = {}

                # Copy top-level fields
                for key, value in vehicle.items():
                    if key != 'params' and not isinstance(value, (dict, list)):
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
    print("AvitoScraping Agent")
    print("==================")

    # Initialize agent with proxy enabled
    agent = AvitoScrapingAgent(use_llm=True, use_proxy=True)

    # Scrape a single category as a test with limited parameters
    # Use very conservative limits to avoid rate limiting
    vehicles = await agent.scrape_category("trucks", max_pages=1, max_vehicles=3)

    # Save results
    if vehicles:
        agent.save_to_json(vehicles, "scraped_vehicles.json")
        agent.save_to_csv(vehicles, "scraped_vehicles.csv")

    print("\nScraping completed!")

def main():
    """Main function."""
    if not SCRAPING_LIBS_AVAILABLE:
        print("Error: Required libraries not available. Install with:")
        print("pip install aiohttp beautifulsoup4 pandas")
        return

    # Run async main
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
