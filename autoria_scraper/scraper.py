"""Scraper module for AutoRia."""
import asyncio
import re
from typing import Optional, Set
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import CONFIG
from .database import db


class AutoRiaScraper:
    """AutoRia scraper class."""

    def __init__(self):
        """Initialize scraper with config."""
        self.config = CONFIG["scraper"]
        self.start_url = self.config["start_url"]
        self.concurrency = self.config["concurrency"]
        self.request_timeout = self.config["request_timeout"]
        self.request_delay = self.config["request_delay"]
        self.max_retries = self.config["max_retries"]
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_urls: Set[str] = set()
        self.selenium_driver = None

    async def __aenter__(self):
        """Context manager enter."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.cleanup()

    async def initialize(self):
        """Initialize scraper resources."""
        logger.info("Initializing scraper...")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout)
        )
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.selenium_driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        await db.connect()
        logger.info("Scraper initialized")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up scraper resources...")
        if self.session and not self.session.closed:
            await self.session.close()
        
        if self.selenium_driver:
            self.selenium_driver.quit()
            
        logger.info("Scraper resources cleaned up")

    async def scrape(self):
        """Run the scraping process."""
        logger.info("Starting scraping process...")
        try:
            await self.process_listing_pages()
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            await self.cleanup()
        logger.info("Scraping process completed")

    async def process_listing_pages(self):
        """Process all listing pages."""
        logger.info(f"Starting from URL: {self.start_url}")
        
        current_page_url = self.start_url
        page_num = 1
        
        while current_page_url:
            logger.info(f"Processing listing page {page_num}: {current_page_url}")
            car_urls, next_page_url = await self._extract_car_urls_and_next_page(current_page_url)
            
            if not car_urls:
                logger.warning(f"No car URLs found on page {page_num}")
                break
                
            logger.info(f"Found {len(car_urls)} car URLs on page {page_num}")
            
            # Process car detail pages concurrently with limited concurrency
            semaphore = asyncio.Semaphore(self.concurrency)
            tasks = [
                self._process_car_page_with_semaphore(car_url, semaphore)
                for car_url in car_urls
                if car_url not in self.processed_urls
            ]
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful results
                success_count = sum(1 for r in results if isinstance(r, bool) and r)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                
                logger.info(
                    f"Processed {len(tasks)} cars from page {page_num}: "
                    f"{success_count} successful, {error_count} errors"
                )
            
            # Move to next page or exit
            if not next_page_url:
                logger.info("No more pages to process")
                break
                
            current_page_url = next_page_url
            page_num += 1
            
            # Short delay between pages to be nice to the server
            await asyncio.sleep(self.request_delay)

    async def _extract_car_urls_and_next_page(self, page_url):
        """
        Extract car URLs and next page URL from a listing page.
        Returns (car_urls, next_page_url)
        """
        car_urls = []
        next_page_url = None
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(page_url) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to fetch listing page: {page_url}, "
                            f"status: {response.status}"
                        )
                        await asyncio.sleep(self.request_delay * (attempt + 1))
                        continue
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, "lxml")
                    
                    # Extract car URLs
                    car_links = soup.select("div.content-bar > a.m-link-ticket")
                    car_urls = [urljoin(page_url, link.get("href")) for link in car_links]
                    
                    # Extract next page URL
                    next_page_element = soup.select_one("a.js-next")
                    if next_page_element and next_page_element.get("href"):
                        next_page_url = urljoin(page_url, next_page_element.get("href"))
                    
                    return car_urls, next_page_url
            except Exception as e:
                logger.error(f"Error extracting car URLs from {page_url}: {e}")
                await asyncio.sleep(self.request_delay * (attempt + 1))
        
        logger.warning(f"Failed to extract car URLs after {self.max_retries} attempts")
        return [], None

    async def _process_car_page_with_semaphore(self, car_url, semaphore):
        """Process a car page with a semaphore for concurrency control."""
        async with semaphore:
            try:
                if car_url in self.processed_urls:
                    return False
                
                car_data = await self._extract_car_data(car_url)
                if car_data:
                    self.processed_urls.add(car_url)
                    saved = await db.save_car(car_data)
                    return saved
                
                return False
            except Exception as e:
                logger.error(f"Error processing car page {car_url}: {e}")
                raise

    async def _extract_car_data(self, car_url):
        """Extract car data from a detail page."""
        logger.debug(f"Extracting data from: {car_url}")
        
        for attempt in range(self.max_retries):
            try:
                # For phone number we need to use Selenium to click the button
                # and extract the phone number
                self.selenium_driver.get(car_url)
                
                # Wait for page to load
                WebDriverWait(self.selenium_driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "auto-content"))
                )
                
                # Extract basic data
                title_element = self.selenium_driver.find_element(By.CLASS_NAME, "auto-content__title")
                title = title_element.text.strip() if title_element else ""
                
                # Extract price
                price_element = self.selenium_driver.find_element(By.CLASS_NAME, "price_value")
                price_text = price_element.text.strip() if price_element else "0"
                price_usd = self._extract_price(price_text)
                
                # Extract odometer
                try:
                    odometer_element = self.selenium_driver.find_element(
                        By.XPATH, "//div[contains(@class, 'base-information')]/span[contains(text(), 'тис')]"
                    )
                    odometer_text = odometer_element.text.strip() if odometer_element else "0"
                    odometer = self._extract_odometer(odometer_text)
                except Exception:
                    odometer = 0
                
                # Extract username
                try:
                    username_element = self.selenium_driver.find_element(By.CLASS_NAME, "seller_info_name")
                    username = username_element.text.strip() if username_element else ""
                except Exception:
                    username = ""
                
                # Click to show phone number
                try:
                    show_phone_button = self.selenium_driver.find_element(
                        By.XPATH, "//a[contains(@class, 'phone_show_link')]"
                    )
                    show_phone_button.click()
                    
                    # Wait for phone to appear
                    WebDriverWait(self.selenium_driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "phone"))
                    )
                    
                    phone_elements = self.selenium_driver.find_elements(By.CLASS_NAME, "phone")
                    phone_numbers = []
                    for elem in phone_elements:
                        if elem.text and elem.text.strip():
                            phone_numbers.append(elem.text.strip())
                    
                    phone_number = self._extract_phone_number(phone_numbers[0] if phone_numbers else "")
                except Exception:
                    phone_number = 0
                
                # Extract main image
                try:
                    image_element = self.selenium_driver.find_element(
                        By.XPATH, "//div[contains(@class, 'gallery-order')]/picture/source"
                    )
                    image_url = image_element.get_attribute("srcset") if image_element else ""
                except Exception:
                    image_url = ""
                
                # Count all images
                try:
                    small_images = self.selenium_driver.find_elements(
                        By.XPATH, "//div[contains(@class, 'preview-gallery')]/ul/li"
                    )
                    images_count = len(small_images)
                except Exception:
                    images_count = 0
                
                # Extract car number and VIN
                car_number = ""
                car_vin = ""
                
                try:
                    # Look for car number
                    number_element = self.selenium_driver.find_element(
                        By.XPATH, "//span[contains(@class, 'state-num')]"
                    )
                    car_number = number_element.text.strip() if number_element else ""
                except Exception:
                    pass
                
                try:
                    # Look for VIN
                    vin_element = self.selenium_driver.find_element(
                        By.XPATH, "//span[contains(@class, 'label-vin')]"
                    )
                    car_vin = vin_element.text.strip() if vin_element else ""
                except Exception:
                    pass
                
                return {
                    "url": car_url,
                    "title": title,
                    "price_usd": price_usd,
                    "odometer": odometer,
                    "username": username,
                    "phone_number": phone_number,
                    "image_url": image_url,
                    "images_count": images_count,
                    "car_number": car_number,
                    "car_vin": car_vin,
                }
            except Exception as e:
                logger.error(f"Error extracting car data from {car_url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.request_delay * (attempt + 1))
                else:
                    logger.warning(f"Failed to extract car data after {self.max_retries} attempts")
                    return None

    def _extract_price(self, price_text):
        """Extract price as an integer."""
        if not price_text:
            return 0
            
        # Remove non-digit characters
        digits = re.sub(r'[^\d]', '', price_text)
        return int(digits) if digits else 0

    def _extract_odometer(self, odometer_text):
        """
        Extract odometer value as an integer in kilometers.
        Convert from 'тис. км' (thousand km) to km.
        """
        if not odometer_text:
            return 0
            
        # Extract the number part
        number_match = re.search(r'(\d+[.,]?\d*)', odometer_text)
        if not number_match:
            return 0
            
        # Convert to float and then to integer kilometers
        try:
            number = number_match.group(1).replace(',', '.')
            thousand_km = float(number)
            return int(thousand_km * 1000)
        except Exception:
            return 0

    def _extract_phone_number(self, phone_text):
        """Extract phone number as an integer."""
        if not phone_text:
            return 0
            
        # Remove non-digit characters
        digits = re.sub(r'[^\d]', '', phone_text)
        return int(digits) if digits else 0


# Scraper singleton instance
scraper = AutoRiaScraper()


async def run_scraper():
    """Run the scraper."""
    logger.info("Running scraper...")
    async with scraper:
        await scraper.scrape()
    logger.info("Scraper finished") 