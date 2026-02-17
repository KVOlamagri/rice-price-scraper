"""
JSON parser for Carrefour product data.
Extracts product information from JSON embedded in page content.
"""

import json
import re
import logging
from typing import List, Optional, Dict, Any
from src.models import Product
from src.utils import extract_pack_size, filter_by_category

logger = logging.getLogger(__name__)


def extract_json_products(page_content: str, base_url: str, country: str) -> List[Product]:
    """
    Extract products from JSON data embedded in page HTML.
    
    Args:
        page_content: HTML content of the page
        base_url: Base URL for constructing product URLs
        country: Country code (uae, ksa)
        
    Returns:
        List of Product objects
    """
    products = []
    
    try:
        # Step 1: Find the dataLayer script with products
        # Look for window.dataLayer.push with products array
        start_marker = 'window.dataLayer.push(['
        products_marker = '"products":['
        
        start_idx = page_content.find(start_marker)
        if start_idx == -1:
            logger.debug("No dataLayer.push found")
            return []
        
        # Find products array within the dataLayer push
        products_start = page_content.find(products_marker, start_idx)
        if products_start == -1:
            logger.debug("No products array found in dataLayer")
            return []
        
        # Find the start of the products array
        array_start = products_start + len('"products":')
        
        # Find the matching closing bracket for the products array
        # Count brackets to find the end
        bracket_count = 0
        array_end = array_start
        in_string = False
        escape_next = False
        
        for i in range(array_start, min(array_start + 2000000, len(page_content))):
            char = page_content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        array_end = i + 1
                        break
        
        if array_end <= array_start:
            logger.debug("Could not find end of products array")
            return []
        
        # Extract and parse the JSON array
        json_str = page_content[array_start:array_end]
        
        try:
            product_data = json.loads(json_str)
            if isinstance(product_data, list):
                logger.info(f"Found {len(product_data)} products in JSON data")
                
                # Parse each product
                for item in product_data:
                    product = parse_json_product(item, base_url, country)
                    if product:
                        products.append(product)
                
                logger.info(f"Successfully parsed {len(products)} products from JSON")
            else:
                logger.debug("Products data is not a list")
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode error: {str(e)[:200]}")
            return []
        
    except Exception as e:
        logger.error(f"Error extracting JSON products: {e}")
    
    return products


def parse_json_product(data: Dict[str, Any], base_url: str, country: str) -> Optional[Product]:
    """
    Parse a single product from JSON data.
    
    Args:
        data: Product data dictionary
        base_url: Base URL
        country: Country code
        
    Returns:
        Product object or None
    """
    try:
        # Extract product name
        product_name = data.get('name', '').strip()
        if not product_name or len(product_name) < 5:
            return None
        
        # Filter by category
        category = filter_by_category(product_name)
        if not category:
            return None
        
        # Extract price information
        price_info = data.get('price', {})
        regular_price = float(price_info.get('price', 0))
        
        # Check for discount/promo price
        promo_price = None
        discount_info = price_info.get('discount', {})
        if discount_info:
            promo_price = float(discount_info.get('price', 0))
        
        is_promo = promo_price is not None and promo_price > 0 and promo_price < regular_price
        
        # Extract currency
        currency = price_info.get('currency', 'AED' if country == 'uae' else 'SAR')
        
        # Extract pack size
        size = data.get('size', '')
        pack_size = size if size else extract_pack_size(product_name)
        
        # Extract availability
        availability_info = data.get('availability', {})
        stock_info = data.get('stock', {})
        is_available = availability_info.get('isAvailable', False)
        stock_status = stock_info.get('stockLevelStatus', 'unknown')
        
        if not is_available or stock_status == 'outOfStock':
            availability = 'Out of Stock'
        elif stock_status == 'lowStock':
            availability = 'Low Stock'
        else:
            availability = 'In Stock'
        
        # Extract product URL
        links = data.get('links', {})
        product_url_info = links.get('productUrl', {})
        product_path = product_url_info.get('href', '')
        
        if product_path:
            product_url = product_path if product_path.startswith('http') else f"{base_url}{product_path}"
        else:
            product_url = base_url
        
        # Create Product object
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
        
        logger.debug(f"Parsed JSON product: {product_name} - {currency}{regular_price}")
        return product
        
    except Exception as e:
        logger.debug(f"Error parsing JSON product: {e}")
        return None
