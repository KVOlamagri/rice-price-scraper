"""Command-line interface for rice price scraper."""
import argparse
import yaml
import logging
from pathlib import Path
from src.logger import setup_logging
from src.scraper import RicePriceScraper
from src.exporter import DataExporter


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Rice Price Scraper - Extract rice prices from Carrefour and Lulu'
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '-r', '--retailer',
        type=str,
        choices=['carrefour', 'lulu', 'all'],
        default='all',
        help='Retailer to scrape (default: all)'
    )
    
    parser.add_argument(
        '-n', '--country',
        type=str,
        choices=['uae', 'ksa', 'all'],
        default='all',
        help='Country to scrape (default: all)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Custom output filename (without extension)'
    )
    
    parser.add_argument(
        '--csv-only',
        action='store_true',
        help='Export only to CSV'
    )
    
    parser.add_argument(
        '--excel-only',
        action='store_true',
        help='Export only to Excel'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {args.config}")
        return 1
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML configuration: {e}")
        return 1
    
    # Override output settings based on CLI args
    if args.csv_only:
        config['output']['excel_enabled'] = False
        config['output']['csv_enabled'] = True
    elif args.excel_only:
        config['output']['csv_enabled'] = False
        config['output']['excel_enabled'] = True
    
    # Override log level if verbose
    if args.verbose:
        config['logging']['level'] = 'DEBUG'
    
    # Setup logging
    setup_logging(config.get('logging', {}))
    logger = logging.getLogger(__name__)
    
    logger.info("Rice Price Scraper Started")
    logger.info(f"Configuration loaded from: {args.config}")
    
    # Initialize scraper
    scraper = RicePriceScraper(config)
    exporter = DataExporter(config.get('output', {}))
    
    # Run scraping based on arguments
    all_products = []
    
    try:
        if args.retailer == 'all':
            # Scrape all retailers
            all_products = scraper.scrape_all()
        else:
            # Scrape specific retailer
            country = None if args.country == 'all' else args.country
            all_products = scraper.scrape_retailer(args.retailer, country)
        
        # Export combined results
        if all_products:
            exporter.export_combined(all_products, args.output)
            logger.info(f"Successfully scraped {len(all_products)} products")
        else:
            logger.warning("No products were scraped")
        
        logger.info("Rice Price Scraper Completed Successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
