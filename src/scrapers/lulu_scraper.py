"""Lulu scraper using Playwright for dynamic pages."""
import logging
import time
import re
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from src.models import Product
from src.utils import extract_pack_size, filter_by_category, clean_price


logger = logging.getLogger(__name__)


class LuluScraper:
    """Scraper for Lulu using Playwright for dynamic content."""
    
    def __init__(self, config: dict):
        """
        Initialize Lulu scraper.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.retry_config = config.get('retry', {})
        self.filters = config.get('filters', {})
    
    def scrape(self, country: str) -> List[Product]:
        """
        Scrape Lulu for the given country.
        
        Args:
            country: Country code ('uae' or 'ksa')
            
        Returns:
            List of Product objects
        """
        logger.info(f"Starting Lulu scrape for {country.upper()}")
        
        country_config = self.config['lulu'].get(country)
        if not country_config:
            logger.error(f"No configuration for Lulu {country}")
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
                logger.info(f"Total products from Lulu {country.upper()}: {len(products)}")
                
            except Exception as e:
                logger.error(f"Error during Lulu scraping for {country}: {e}")
        
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
        full_url = f"{search_url}?search_text={search_term.replace(' ', '+')}"
        
        attempt = 0
        max_attempts = self.retry_config.get('max_attempts', 3)
        delay = self.retry_config.get('delay_seconds', 2)
        backoff = self.retry_config.get('backoff_multiplier', 2)
        
        while attempt < max_attempts:
            try:
                logger.info(f"Navigating to: {full_url}")
                page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for page to load - try multiple strategies
                try:
                    page.wait_for_load_state('load', timeout=20000)
                    time.sleep(3)  # Additional wait for dynamic content
                    
                    # Wait specifically for product content to appear
                    logger.info("Waiting for products to load...")
                    try:
                        # Try waiting for common product container patterns
                        page.wait_for_selector('article, [data-testid*="product"], [class*="productCard"], [class*="product-card"], div[class*="grid"] > div', timeout=10000)
                        time.sleep(2)  # Extra wait for all products to render
                    except Exception as e:
                        logger.warning(f"Timeout waiting for product selector: {e}")
                        time.sleep(3)
                except Exception:
                    time.sleep(3)  # Fallback wait
                
                # Scroll to load more products
                self._scroll_page(page)
                
                # Optional: Save HTML for debugging
                if logger.level <= 10:  # DEBUG level
                    try:
                        html_path = f"output/debug_lulu_{country}.html"
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
        Scroll page to trigger lazy loading and load all products.
        
        Args:
            page: Playwright page object
        """
        try:
            logger.info("Scrolling to load all products...")
            previous_height = 0
            max_scrolls = 10  # Balanced approach for loading products
            stable_count = 0  # Count consecutive stable heights
            
            for scroll_num in range(max_scrolls):
                # Get current height
                current_height = page.evaluate('document.body.scrollHeight')
                
                # Scroll to bottom
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1.5)  # Wait for content to load
                
                # Get new height
                new_height = page.evaluate('document.body.scrollHeight')
                
                # If height hasn't changed, we've reached the end
                if new_height == previous_height:
                    stable_count += 1
                    if stable_count >= 2:  # If stable for 2 scrolls, we're done
                        logger.info(f"Reached end of page after {scroll_num + 1} scrolls")
                        break
                else:
                    stable_count = 0
                    
                previous_height = new_height
                logger.debug(f"Scroll {scroll_num + 1}: height {new_height}px")
            
            # Final wait for any remaining content
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error scrolling page: {e}")
    
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
        
        # Lulu uses product card links - get the parent containers
        product_selectors = [
            # Try to get the full product card container that wraps the link
            'a[href*="/p/"]',  # Product links themselves
        ]
        
        product_elements = []
        for selector in product_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    # For link elements, we want unique product links only
                    unique_products = []
                    seen_urls = set()
                    
                    for elem in elements:
                        try:
                            href = elem.get_attribute('href')
                            if href and '/p/' in href:
                                if href not in seen_urls:
                                    seen_urls.add(href)
                                    unique_products.append(elem)
                        except Exception:
                            continue
                    
                    if unique_products:
                        product_elements = unique_products
                        logger.info(f"Found {len(unique_products)} unique products using selector: {selector}")
                        break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        if not product_elements:
            logger.warning("No products found on page")
            # Try to get all text content for debugging
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
            # For 'a' elements (product links), get the text content
            product_name = None
            
            try:
                # Get text from the link element itself or look for title attribute
                product_name = element.get_attribute('title')
                
                if not product_name or len(product_name) < 5:
                    # Try inner text
                    product_name = element.inner_text().strip()
                    
                if not product_name or len(product_name) < 5:
                    # Look in child elements
                    name_elem = element.query_selector('img')
                    if name_elem:
                        alt_text = name_elem.get_attribute('alt')
                        if alt_text and len(alt_text) > 5:
                            product_name = alt_text
                
                if product_name:
                    # Clean up the name
                    product_name = product_name.strip()
                    # Take the first meaningful line if multi-line
                    lines = [l.strip() for l in product_name.split('\n') if l.strip()]
                    if lines:
                        # Find the line with rice/basmati/jasmine
                        for line in lines:
                            if len(line) > 10 and any(kw in line.lower() for kw in ['rice', 'basmati', 'jasmine', 'sella']):
                                product_name = line
                                break
                        else:
                            product_name = lines[0] if lines else None
                    
                    logger.debug(f"Extracted product name: {product_name}")
                    
            except Exception as e:
                logger.debug(f"Error extracting product name: {e}")
            
            # Fallback to selectors
            if not product_name:
                name_selectors = [
                    'h3', 'h4', 'h2',
                    '[class*="name"]',
                    '[class*="title"]',
                    '[class*="product"][class*="name"]',
                    '[data-testid*="name"]',
                    'span[class*="text"]'
                ]
                
                for selector in name_selectors:
                    name_elem = element.query_selector(selector)
                    if name_elem:
                        product_name = name_elem.inner_text().strip()
                        if len(product_name) > 5:
                            break
            
            if not product_name:
                logger.debug("No product name found, skipping element")
                return None
            
            # Filter by category
            category = filter_by_category(product_name, self.filters)
            if not category:
                logger.debug(f"Product '{product_name}' did not match any category filter")
                return None
            
            # Extract prices - Lulu has prices in data-testid="product-price"
            regular_price = 0.0
            import re
            
            try:
                # Use Playwright to find the price in the product card
                price_info = page.evaluate(r'''(linkElement) => {
                    // Navigate up to the product card container
                    let container = linkElement.closest('div[class*="rounded-"]') || 
                                   linkElement.closest('div') || 
                                   linkElement.parentElement;
                    
                    if (!container) return null;
                    
                    // Look for the price span with data-testid
                    let priceSpan = container.querySelector('span[data-testid="product-price"]');
                    if (priceSpan && priceSpan.textContent) {
                        let priceText = priceSpan.textContent.trim();
                        // Extract just the number
                        let match = priceText.match(/(\d+\.?\d*)/);
                        if (match && match[1]) {
                            let price = parseFloat(match[1]);
                            if (price > 0 && price < 10000) {
                                return price;
                            }
                        }
                    }
                    
                    return null;
                }''', element)
                
                if price_info and price_info > 0:
                    regular_price = float(price_info)
                    logger.debug(f"Extracted price from product-price span: {regular_price}")
                    
            except Exception as e:
                logger.debug(f"Error with price extraction: {e}")
            
            # Fallback: Try element.query_selector directly
            if regular_price == 0:
                try:
                    # Get parent container
                    parent = element.evaluate('el => el.closest("div[class*=\\"rounded-\\"]") || el.parentElement')
                    if element:
                        # Try to query selector from element's parent
                        price_spans = element.evaluate('''el => {
                            let container = el.closest('div[class*="rounded-"]') || el.parentElement;
                            if (!container) return [];
                            let spans = container.querySelectorAll('span[data-testid="product-price"]');
                            return Array.from(spans).map(s => s.textContent.trim());
                        }''')
                        
                        if price_spans and len(price_spans) > 0:
                            price_text = price_spans[0]
                            match = re.search(r'(\d+\.?\d*)', price_text)
                            if match:
                                regular_price = float(match.group(1))
                                logger.debug(f"Extracted price from fallback: {regular_price}")
                except Exception as e:
                    logger.debug(f"Fallback price extraction failed: {e}")
            
            # Check for promo price
            promo_selectors = ['.special-price', '.promo-price', '.discount-price', '[data-testid="promo-price"]']
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
            link_elem = element.query_selector('a')
            product_url = base_url
            if link_elem:
                href = link_elem.get_attribute('href')
                if href:
                    product_url = href if href.startswith('http') else f"{base_url}{href}"
            
            # Extract other fields
            pack_size = extract_pack_size(product_name)
            currency = 'AED' if country == 'uae' else 'SAR'
            
            # Check availability
            availability = 'In Stock'
            out_of_stock_indicators = ['.out-of-stock', '.unavailable', '[data-testid="out-of-stock"]']
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
                retailer='Lulu',
                country=country.upper(),
                category=category
            )
            
            logger.debug(f"Parsed product: {product_name}")
            return product
            
        except Exception as e:
            logger.warning(f"Error parsing product: {e}")
            return None
