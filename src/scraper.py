"""Main scraper orchestrator."""
import logging
from typing import List
from src.models import Product
from src.scrapers.carrefour_scraper import CarrefourScraper
from src.scrapers.lulu_scraper import LuluScraper
from src.exporter import DataExporter


logger = logging.getLogger(__name__)


class RicePriceScraper:
    """Main orchestrator for rice price scraping."""
    
    def __init__(self, config: dict):
        """
        Initialize rice price scraper.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.carrefour_scraper = CarrefourScraper(config)
        self.lulu_scraper = LuluScraper(config)
        self.exporter = DataExporter(config.get('output', {}))
    
    def scrape_all(self) -> List[Product]:
        """
        Scrape all retailers and countries.
        
        Returns:
            List of all Product objects
        """
        logger.info("=" * 80)
        logger.info("Starting rice price scraping")
        logger.info("=" * 80)
        
        all_products = []
        
        # Scrape Carrefour
        for country in ['uae', 'ksa']:
            try:
                logger.info(f"\n{'=' * 40}")
                logger.info(f"Scraping Carrefour {country.upper()}")
                logger.info(f"{'=' * 40}")
                
                products = self.carrefour_scraper.scrape(country)
                all_products.extend(products)
                
                # Export individual results
                self.exporter.export(products, 'carrefour', country)
                
            except Exception as e:
                logger.error(f"Error scraping Carrefour {country}: {e}", exc_info=True)
        
        # Scrape Lulu
        for country in ['uae', 'ksa']:
            try:
                logger.info(f"\n{'=' * 40}")
                logger.info(f"Scraping Lulu {country.upper()}")
                logger.info(f"{'=' * 40}")
                
                products = self.lulu_scraper.scrape(country)
                all_products.extend(products)
                
                # Export individual results
                self.exporter.export(products, 'lulu', country)
                
            except Exception as e:
                logger.error(f"Error scraping Lulu {country}: {e}", exc_info=True)
        
        logger.info("=" * 80)
        logger.info(f"Scraping complete. Total products: {len(all_products)}")
        logger.info("=" * 80)
        
        return all_products
    
    def scrape_retailer(self, retailer: str, country: str = None) -> List[Product]:
        """
        Scrape a specific retailer.
        
        Args:
            retailer: Retailer name ('carrefour' or 'lulu')
            country: Optional country filter ('uae' or 'ksa')
            
        Returns:
            List of Product objects
        """
        products = []
        countries = [country] if country else ['uae', 'ksa']
        
        for ctry in countries:
            try:
                if retailer.lower() == 'carrefour':
                    logger.info(f"Scraping Carrefour {ctry.upper()}")
                    prods = self.carrefour_scraper.scrape(ctry)
                elif retailer.lower() == 'lulu':
                    logger.info(f"Scraping Lulu {ctry.upper()}")
                    prods = self.lulu_scraper.scrape(ctry)
                else:
                    logger.error(f"Unknown retailer: {retailer}")
                    continue
                
                products.extend(prods)
                self.exporter.export(prods, retailer, ctry)
                
            except Exception as e:
                logger.error(f"Error scraping {retailer} {ctry}: {e}", exc_info=True)
        
        return products
