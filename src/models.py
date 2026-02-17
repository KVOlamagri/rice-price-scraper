"""Data models for rice price scraping."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    """Represents a scraped rice product."""
    product_name: str
    pack_size: str
    currency: str
    regular_price: float
    promo_price: Optional[float]
    is_promo: bool
    availability: str
    product_url: str
    retailer: str
    country: str
    category: str
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Convert product to dictionary."""
        return {
            'product_name': self.product_name,
            'pack_size': self.pack_size,
            'currency': self.currency,
            'regular_price': self.regular_price,
            'promo_price': self.promo_price,
            'is_promo': self.is_promo,
            'availability': self.availability,
            'product_url': self.product_url,
            'retailer': self.retailer,
            'country': self.country,
            'category': self.category,
            'scraped_at': self.scraped_at.isoformat()
        }
