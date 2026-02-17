"""Carrefour scraper using Playwright (same approach as Lulu)."""
import logging
import time
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from src.models import Product
from src.utils import extract_pack_size, filter_by_category, clean_price


logger = logging.getLogger(__name__)


class CarrefourScraper:
    """Scraper for Carrefour using Playwright for dynamic content."""
    
    def __init__(self, config: dict):
        """
        Initialize Carrefour scraper.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.retry_config = config.get('retry', {})
        self.filters = config.get('filters', {})
    
    def scrape(self, country: str) -> List[Product]:
        """
        Scrape Carrefour for the given country.
        
        Args:
            country: Country code ('uae' or 'ksa')
            
        Returns:
            List of Product objects
        """
        logger.info(f"Starting Carrefour scrape for {country.upper()}")
        
        country_config = self.config['carrefour'].get(country)
        if not country_config:
            logger.error(f"No configuration for Carrefour {country}")
            return []
        
        products = []
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Scrape products
                products = self._scrape_with_page(page, country_config, country)
                
                browser.close()
                logger.info(f"Total products from Carrefour {country.upper()}: {len(products)}")
                
            except Exception as e:
                logger.error(f"Error during Carrefour scraping for {country}: {e}")
        
        return products
    
    def _scrape_with_page(self, page: Page, country_config: dict, country: str) -> List[Product]:
        """
        Scrape products using Playwright page.
        
        Args:
            page: Playwright page object
            country_config: Country-specific configuration
            country: Country code
            
        Returns:
            List of Product objects
        """
        products = []
        search_url = country_config['search_url']
        search_term = country_config['search_term']
        
        # Navigate to search page
        full_url = f"{search_url}?keyword={search_term.replace(' ', '+')}"
        
        attempt = 0
        max_attempts = self.retry_config.get('max_attempts', 3)
        delay = self.retry_config.get('delay_seconds', 2)
        backoff = self.retry_config.get('backoff_multiplier', 2)
        
        while attempt < max_attempts:
            try:
                logger.info(f"Navigating to: {full_url}")
                page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for page to load
                try:
                    page.wait_for_load_state('load', timeout=20000)
                    time.sleep(3)  # Additional wait for dynamic content
                except Exception:
                    time.sleep(3)  # Fallback wait
                
                # Scroll to load more products
                self._scroll_page(page)
                
                # Optional: Save HTML for debugging
                if logger.level <= 10:  # DEBUG level
                    try:
                        html_path = f"output/debug_carrefour_{country}.html"
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(page.content())
                        logger.debug(f"Saved page HTML to {html_path}")
                    except Exception as e:
                        logger.debug(f"Could not save HTML: {e}")
                
                # Extract products
                products = self._extract_products(page, country_config['base_url'], country)
                break
                
            except PlaywrightTimeout as e:
                attempt += 1
                logger.warning(f"Attempt {attempt}/{max_attempts} timed out: {e}")
                
                if attempt < max_attempts:
                    time.sleep(delay)
                    delay *= backoff
                else:
                    logger.error("Max retries reached")
                    raise
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        
        return products
    
    def _scroll_page(self, page: Page):
        """
        Scroll page and click 'Load More' button to load all products.
        
        Args:
            page: Playwright page object
        """
        try:
            previous_height = 0
            max_scrolls = 10
            
            for scroll_attempt in range(max_scrolls):
                # Get current scroll height
                current_height = page.evaluate('document.body.scrollHeight')
                
                # Scroll to bottom
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
                
                # Try to click "Load More" button
                try:
                    load_more_clicked = page.evaluate('''() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const loadMore = buttons.find(btn => 
                            btn.textContent.toLowerCase().includes('load') || 
                            btn.textContent.toLowerCase().includes('more')
                        );
                        if (loadMore && loadMore.offsetParent !== null) {
                            loadMore.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    if load_more_clicked:
                        logger.info(f"Clicked 'Load More' button (scroll #{scroll_attempt + 1})")
                        time.sleep(3)
                    
                except Exception as e:
                    logger.debug(f"No Load More button: {e}")
                
                # Check if page height changed
                new_height = page.evaluate('document.body.scrollHeight')
                if new_height == previous_height:
                    # No new content loaded, stop scrolling
                    logger.info(f"No more content to load after {scroll_attempt + 1} scrolls")
                    break
                    
                previous_height = current_height
            
            # Scroll back to top
            page.evaluate('window.scrollTo(0, 0)')
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error during page scroll: {e}")
    
    def _extract_products(self, page: Page, base_url: str, country: str) -> List[Product]:
        """
        Extract products from the page.
        
        Args:
            page: Playwright page object
            base_url: Base URL for constructing product URLs
            country: Country code
            
        Returns:
            List of Product objects
        """
        products = []
        
        # Try JSON extraction first (more reliable for Carrefour)
        try:
            from src.scrapers.carrefour_json_parser import extract_json_products
            page_content = page.content()
            products = extract_json_products(page_content, base_url, country)
            
            if products:
                logger.info(f"Extracted {len(products)} products from JSON data")
                return products
            else:
                logger.info("No products found in JSON, falling back to HTML parsing")
        except Exception as e:
            logger.warning(f"JSON extraction failed: {e}, using HTML parsing")
        
        #Try multiple selectors for Carrefour
        product_selectors = [
            'div[class*="product"]',  # Product card container
            'article',
            'li[class*="product"]',
            '[data-testid*="product"]',
            'div[class*="relative"][class*="flex"]'  # Common container class on Carrefour
        ]
        
        product_elements = []
        for selector in product_selectors:
            try:
                elements = page.query_selector_all(selector)
                # Filter to elements that contain product links
                filtered = [el for el in elements if el.query_selector('a[href*="/mafuae/en/"]') or el.query_selector('a[href*="/p/"]')]
                if filtered and len(filtered) > 5:  # Need multiple products
                    product_elements = filtered
                    logger.info(f"Found {len(filtered)} product containers using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
        
        # If no containers found, fallback to direct link selection
        if not product_elements:
            logger.info("Falling back to direct link selection")
            product_elements = page.query_selector_all('a[href*="/mafuae/en/"]')
            logger.info(f"Found {len(product_elements)} product links")
        
        if not product_elements:
            logger.warning("No products found on page")
            page_content = page.content()
            logger.debug(f"Page title: {page.title()}")
            logger.warning(f"Page URL: {page.url}")
            return products
        
        for element in product_elements:
            try:
                product = self._parse_product_element(element, base_url, country)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"Error parsing product element: {e}")
                continue
        
        return products
    
    def _parse_product_element(self, element, base_url: str, country: str) -> Product:
        """
        Parse a single product element.
        
        Args:
            element: Playwright element
            base_url: Base URL for constructing product URLs
            country: Country code
            
        Returns:
            Product object or None
        """
        try:
            # Extract product name - try to get from link text or child elements
            product_name = None
            
            # First, check if element itself is a link or find link within
            link_elem = None
            try:
                if element.evaluate('el => el.tagName').lower() == 'a':
                    link_elem = element
                else:
                    link_elem = element.query_selector('a[href*="/mafuae/en/"], a[href*="/p/"]')
            except Exception:
                pass
            
            if link_elem:
                try:
                    product_name = link_elem.inner_text().strip()
                except Exception:
                    pass
            
            # Fallback to text extraction
            if not product_name or len(product_name) <5:
                try:
                    all_text = element.inner_text().strip()
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    for line in lines:
                        if len(line) > 10 and not line.replace('.', '').replace(',', '').isdigit():
                            if any(keyword in line.lower() for keyword in ['rice', 'basmati', 'jasmine', 'sella']):
                                product_name = line
                                break
                except Exception:
                    pass
            
            if not product_name or len(product_name) < 5:
                return None
            
            # Filter by category
            category = filter_by_category(product_name, self.filters)
            if not category:
                return None
            
            # Extract prices - Carrefour UAE splits prices into multiple divs
            regular_price = 0.0
            
            # Try to find price container (force-ltr class often contains prices)
            try:
                # Look for the price container
                price_container = element.query_selector('[class*="force-ltr"]')
                if not price_container:
                    price_container = element.query_selector('[class*="items-center"][class*="ltr"]')
                
                if price_container:
                    #Get all text from price container
                    price_text = price_container.inner_text().strip()
                    # Try to extract number from text (e.g., "28.79AED" or "28\n.79\nAED")
                    import re
                    # Remove spaces and newlines to make parsing easier
                    clean_text = re.sub(r'\s+', '', price_text)
                    # Look for patterns like "28.79" or ".79" after a number
                    price_match = re.search(r'(\d+)\.(\d+)', clean_text)
                    if price_match:
                        main_part = price_match.group(1)
                        decimal_part = price_match.group(2)
                        regular_price = float(f"{main_part}.{decimal_part}")
                    else:
                        # Fallback: just get the integer part
                        int_match = re.search(r'(\d+)', clean_text)
                        if int_match:
                            regular_price = float(int_match.group(1))
            except Exception as e:
                logger.debug(f"Price container extraction failed: {e}")
            
            # Fallback: try to find separate price elements
            if regular_price == 0:
                try:
                    # Look for bold/large text that might be the price
                    price_elems = element.query_selector_all('[class*="font-bold"], [class*="text-lg"], [class*="text-xl"]')
                    price_parts = []
                    for elem in price_elems:
                        text = elem.inner_text().strip()
                        if text and (text.isdigit() or '.' in text):
                            price_parts.append(text)
                   
                    if price_parts:
                        # Combine parts (e.g., ['28', '.79'] -> '28.79')
                        price_str = ''.join(price_parts)
                        regular_price = clean_price(price_str)
                except Exception as e:
                    logger.debug(f"Price parts extraction failed: {e}")
            
            # Check for promo price
            promo_selectors = [
                '[class*="special"]',
                '[class*="promo"]',
                '[class*="discount"]',
                '[class*="sale"]'
            ]
            promo_price = None
            
            for selector in promo_selectors:
                promo_elem = element.query_selector(selector)
                if promo_elem:
                    promo_text = promo_elem.inner_text().strip()
                    promo_price = clean_price(promo_text)
                    if promo_price > 0:
                        break
            
            is_promo = promo_price is not None and promo_price < regular_price
            
            # Extract product URL
            product_url = base_url
            
            # Find the link element (might be same as element or child)
            try:
                if element.evaluate('el => el.tagName').lower() == 'a':
                    href = element.get_attribute('href')
                    if href:
                        product_url = href if href.startswith('http') else f"{base_url}{href}"
                else:
                    link_elem = element.query_selector('a[href*="/mafuae/en/"], a[href*="/p/"]')
                    if link_elem:
                        href = link_elem.get_attribute('href')
                        if href:
                            product_url = href if href.startswith('http') else f"{base_url}{href}"
            except Exception as e:
                logger.debug(f"URL extraction failed: {e}")
            
            # Extract other fields
            pack_size = extract_pack_size(product_name)
            currency = 'AED' if country == 'uae' else 'SAR'
            
            # Check availability
            availability = 'In Stock'
            out_of_stock_indicators = [
                '[class*="out-of-stock"]',
                '[class*="unavailable"]',
                'button[disabled]'
            ]
            for selector in out_of_stock_indicators:
                if element.query_selector(selector):
                    availability = 'Out of Stock'
                    break
            
            product = Product(
                product_name=product_name,
                pack_size=pack_size,
                currency=currency,
                regular_price=regular_price,
                promo_price=promo_price,
                is_promo=is_promo,
                availability=availability,
                product_url=product_url,
                retailer='Carrefour',
                country=country.upper(),
                category=category
            )
            
            logger.debug(f"Parsed product: {product_name}")
            return product
            
        except Exception as e:
            logger.warning(f"Error parsing product: {e}")
            return None
