"""
Avito scraper using Playwright to avoid rate limiting.
"""
import os
import sys
import json
import time
import random
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import re
import urllib.parse

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import tools
from utils import LLMProvider

# Try to import required libraries
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    import pandas as pd
    from bs4 import BeautifulSoup
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright is not installed. Install with:")
    print("pip install playwright")
    print("python -m playwright install")

class AvitoPlaywrightScraper:
    """
    Avito scraper using Playwright to avoid rate limiting.
    """

    def __init__(self, use_llm: bool = True, headless: bool = True):
        """
        Initialize the AvitoPlaywrightScraper.

        Args:
            use_llm: Whether to use LLM for data extraction and enhancement
            headless: Whether to run the browser in headless mode
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Install with 'pip install playwright' and 'python -m playwright install'")

        self.use_llm = use_llm
        self.headless = headless
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

    async def initialize_browser(self) -> tuple:
        """
        Initialize the Playwright browser.

        Returns:
            Tuple of (playwright, browser, context)
        """
        # Launch playwright
        playwright = await async_playwright().start()

        # Launch Safari browser instead of Chromium
        # Safari doesn't need the stealth mode arguments as it's less likely to be detected
        browser = await playwright.webkit.launch(
            headless=self.headless
        )

        # Create a context with realistic viewport and user agent
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            locale="ru-RU"
        )

        # Add stealth mode scripts
        await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        """)

        return playwright, browser, context

    async def close_browser(self, playwright, browser):
        """
        Close the Playwright browser.

        Args:
            playwright: Playwright instance
            browser: Browser instance
        """
        await browser.close()
        await playwright.stop()

    async def search_vehicles(self, page: Page, category: str, page_num: int = 1) -> None:
        """
        Navigate to the search page for a specific category.

        Args:
            page: Playwright page
            category: Category key from self.categories
            page_num: Page number
        """
        if category not in self.categories:
            raise ValueError(f"Unknown category '{category}'")

        # Build URL
        url = self.base_url + self.categories[category]

        # Add page parameter
        if page_num > 1:
            url += f"?p={page_num}"

        print(f"Navigating to {url}")

        # Navigate to the page
        await page.goto(url, wait_until="domcontentloaded")

        # Wait for the content to load with fallbacks
        try:
            await page.wait_for_selector("div[data-marker='item']", timeout=10000)
        except Exception:
            try:
                await page.wait_for_selector("div.item", timeout=10000)
            except Exception:
                # If all selectors fail, just wait for the page to load
                await asyncio.sleep(5)

        # Scroll down to load all items
        await self._scroll_page(page)

    async def _scroll_page(self, page: Page) -> None:
        """
        Scroll the page to load all content.

        Args:
            page: Playwright page
        """
        # Get page height
        page_height = await page.evaluate("document.body.scrollHeight")

        # Scroll down in chunks
        viewport_height = await page.evaluate("window.innerHeight")
        scroll_step = viewport_height

        for scroll_position in range(0, page_height, scroll_step):
            await page.evaluate(f"window.scrollTo(0, {scroll_position})")

            # Random delay to mimic human behavior
            await asyncio.sleep(0.5 + random.random() * 1.5)

            # Check if we need to update the page height
            new_page_height = await page.evaluate("document.body.scrollHeight")
            if new_page_height > page_height:
                page_height = new_page_height

    async def parse_search_results(self, page: Page) -> List[Dict[str, Any]]:
        """
        Parse search results page to extract vehicle listings.

        Args:
            page: Playwright page

        Returns:
            List of vehicle dictionaries with basic info and URLs
        """
        # Get page content
        content = await page.content()

        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

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
                f.write(content)
            print("Saved HTML to avito_debug.html for inspection")

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

    async def get_vehicle_details(self, page: Page, url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a vehicle.

        Args:
            page: Playwright page
            url: Vehicle listing URL

        Returns:
            Dictionary with vehicle details or None if failed
        """
        print(f"Getting details for vehicle: {url}")

        try:
            # Navigate to the vehicle page
            response = await page.goto(url, wait_until="domcontentloaded")

            # Check if we got a valid response
            if response.status >= 400:
                print(f"Error: HTTP status {response.status} for URL: {url}")
                return None

            # Wait for the content to load - try different selectors
            try:
                # Try the main title selector
                await page.wait_for_selector("h1[data-marker='item-view/title']", timeout=10000)
            except Exception:
                try:
                    # Try alternative selectors
                    await page.wait_for_selector("h1.title-info-title", timeout=10000)
                except Exception:
                    # If all selectors fail, just wait for the page to load
                    await asyncio.sleep(5)

            # Scroll down to load all content
            await self._scroll_page(page)

            # Get page content
            content = await page.content()

            # Parse vehicle details
            return self.parse_vehicle_details(content, url)

        except Exception as e:
            print(f"Error getting vehicle details: {e}")
            return None

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
        # Initialize browser
        playwright, browser, context = await self.initialize_browser()

        try:
            # Create a new page
            page = await context.new_page()

            # Add random delays to all navigation actions
            await page.route("**/*", lambda route: self._add_random_delay(route))

            # Add more human-like behavior
            # Simulate mouse movements
            await self._simulate_human_behavior(page)

            all_vehicles = []
            page_num = 1

            while page_num <= max_pages and len(all_vehicles) < max_vehicles:
                # Long delay before starting a new page to avoid rate limiting
                await asyncio.sleep(10 + random.random() * 15)  # 10-25 seconds delay

                print(f"Scraping page {page_num} of category '{category}'...")

                # Search for vehicles
                await self.search_vehicles(page, category, page_num)

                # Parse search results
                vehicles = await self.parse_search_results(page)
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
                    await asyncio.sleep(5 + random.random() * 10)  # 5-15 seconds delay

                    # Get vehicle details
                    vehicle_details = await self.get_vehicle_details(page, vehicle["url"])
                    if vehicle_details:
                        all_vehicles.append(vehicle_details)
                        print(f"Added vehicle: {vehicle_details.get('title', 'Unknown')}")

                    # Simulate human behavior between requests
                    await self._simulate_human_behavior(page)

                    # Random delay between requests - much longer to avoid detection
                    await asyncio.sleep(8 + random.random() * 12)  # 8-20 seconds delay

                # Go to next page
                page_num += 1

                # Random delay between pages - very long to avoid detection
                await asyncio.sleep(15 + random.random() * 15)  # 15-30 seconds delay

            print(f"Scraped {len(all_vehicles)} vehicles from category '{category}'")
            return all_vehicles

        finally:
            # Close browser
            await self.close_browser(playwright, browser)

    async def _add_random_delay(self, route):
        """
        Add random delay to navigation actions to mimic human behavior.

        Args:
            route: Playwright route
        """
        # Continue the route after a random delay
        await asyncio.sleep(0.1 + random.random() * 0.3)
        await route.continue_()

    async def _simulate_human_behavior(self, page: Page):
        """
        Simulate human-like behavior on the page.

        Args:
            page: Playwright page
        """
        try:
            # Get viewport size
            viewport = await page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                }
            """)

            # Perform random mouse movements
            for _ in range(random.randint(3, 8)):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])

                # Move mouse with random speed
                await page.mouse.move(x, y, steps=random.randint(5, 15))

                # Random pause between movements
                await asyncio.sleep(0.5 + random.random() * 2)

            # Randomly scroll up and down
            for _ in range(random.randint(2, 5)):
                # Random scroll distance
                scroll_y = random.randint(-300, 300)

                # Scroll
                await page.evaluate(f"window.scrollBy(0, {scroll_y})")

                # Random pause between scrolls
                await asyncio.sleep(1 + random.random() * 3)

            # Sometimes click on a random non-link element (like whitespace)
            if random.random() < 0.3:  # 30% chance
                x = random.randint(viewport['width'] // 4, viewport['width'] * 3 // 4)
                y = random.randint(viewport['height'] // 4, viewport['height'] * 3 // 4)
                await page.mouse.click(x, y)
                await asyncio.sleep(1 + random.random() * 2)

        except Exception as e:
            print(f"Error simulating human behavior: {e}")
            # Continue even if simulation fails

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
    print("AvitoPlaywrightScraper - Enhanced Version")
    print("====================================")
    print("This version uses Safari (WebKit) and human-like behavior to avoid detection")
    print("It will scrape very slowly to avoid IP bans")
    print()

    # Initialize scraper with Safari and visible browser
    scraper = AvitoPlaywrightScraper(use_llm=True, headless=False)  # Set headless=False to see the browser

    # Scrape a single category as a test with very conservative limits
    print("Starting scraping with conservative limits...")
    print("This will take some time due to intentional delays")
    print("Please do not interact with the browser window while scraping")
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
    if not PLAYWRIGHT_AVAILABLE:
        print("Error: Playwright is not installed. Install with:")
        print("pip install playwright")
        print("python -m playwright install")
        return

    # Run async main
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
