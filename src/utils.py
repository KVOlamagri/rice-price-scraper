"""Utility functions for the rice price scraper."""
import re
import logging
from typing import List
from datetime import datetime


logger = logging.getLogger(__name__)


def extract_pack_size(product_name: str) -> str:
    """
    Extract pack size from product name.
    
    Args:
        product_name: Product name string
        
    Returns:
        Pack size string (e.g., '5kg', '1kg', '500g')
    """
    # Common patterns: 5kg, 1kg, 500g, 5 kg, 1 kg, etc.
    patterns = [
        r'(\d+(?:\.\d+)?\s*(?:kg|g|lb|lbs))',
        r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?\s*(?:kg|g|lb|lbs))'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, product_name, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    
    return "Unknown"


def filter_by_category(product_name: str, patterns: dict) -> str:
    """
    Determine product category based on regex patterns.
    Priority: SELLA > BASMATI > JASMINE
    
    Args:
        product_name: Product name to check
        patterns: Dictionary of regex patterns
        
    Returns:
        Category name or None if no match
    """
    product_name_lower = product_name.lower()
    
    # Check for SELLA first (higher priority)
    if re.search(patterns.get('sella_pattern', ''), product_name, re.IGNORECASE):
        return "SELLA"
    # Then check for BASMATI (excluding sella which was already checked)
    elif re.search(patterns.get('basmati_pattern', ''), product_name, re.IGNORECASE):
        return "BASMATI"
    # Finally check for JASMINE
    elif re.search(patterns.get('jasmine_pattern', ''), product_name, re.IGNORECASE):
        return "JASMINE"
    
    return None


def clean_price(price_str: str) -> float:
    """
    Clean and convert price string to float.
    
    Args:
        price_str: Price string (e.g., 'AED 25.50', '25.50', '$25.50')
        
    Returns:
        Price as float
    """
    if not price_str:
        return 0.0
    
    # Remove currency symbols and text
    cleaned = re.sub(r'[^\d.]', '', str(price_str))
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse price: {price_str}")
        return 0.0


def generate_filename(config: dict, retailer: str, country: str, extension: str) -> str:
    """
    Generate output filename based on configuration.
    
    Args:
        config: Output configuration dictionary
        retailer: Retailer name (e.g., 'carrefour', 'lulu')
        country: Country code (e.g., 'uae', 'ksa')
        extension: File extension (e.g., 'csv', 'xlsx')
        
    Returns:
        Formatted filename
    """
    date_str = datetime.now().strftime('%Y%m%d')
    filename_format = config.get('filename_format', 'rice_prices_{date}_{retailer}_{country}.{ext}')
    
    return filename_format.format(
        date=date_str,
        retailer=retailer,
        country=country,
        ext=extension
    )
