# Rice Price Scraper

A Python-based web scraper to extract weekly rice prices from Carrefour and Lulu hypermarkets in UAE and KSA. The scraper focuses on **BASMATI/SELLA** and **JASMINE** rice categories and provides data export in CSV and Excel formats.

## Features

- ✅ **API-first approach** for Carrefour (JSON endpoints)
- ✅ **Playwright-based scraping** for Lulu (dynamic pages)
- ✅ **Multi-country support**: UAE and KSA
- ✅ **Category filtering**: Basmati/Sella and Jasmine rice only
- ✅ **Comprehensive data extraction**:
  - Product name
  - Pack size
  - Currency
  - Regular price
  - Promotional price
  - Promo status
  - Availability
  - Product URL
- ✅ **Retry logic** with exponential backoff
- ✅ **Dual export formats**: CSV and Excel
- ✅ **Flexible CLI interface**
- ✅ **Configurable via YAML**
- ✅ **Comprehensive logging**
- ✅ **Unit tests included**

## Project Structure

```
Code_v1/
├── config.yaml              # Configuration file
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── src/
│   ├── __init__.py
│   ├── models.py           # Data models
│   ├── utils.py            # Utility functions
│   ├── logger.py           # Logging setup
│   ├── exporter.py         # CSV/Excel export
│   ├── scraper.py          # Main orchestrator
│   └── scrapers/
│       ├── __init__.py
│       ├── carrefour_scraper.py  # Carrefour API scraper
│       └── lulu_scraper.py       # Lulu Playwright scraper
├── tests/
│   ├── __init__.py
│   ├── test_utils.py       # Utility tests
│   └── test_scrapers.py    # Scraper tests
├── output/                 # Generated output files
└── logs/                   # Log files
```

## Installation

### 1. Clone or Download the Repository

```bash
cd "c:\Users\kumar.vaibhav\OneDrive - Olam Global Agri Pte Ltd\Desktop\Rice Web Scraping\Code_v1"
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

## Configuration

Edit [config.yaml](config.yaml) to customize scraping parameters:

```yaml
# Scraping Schedule
schedule:
  day: "Monday"
  time: "09:00"
  timezone: "Asia/Dubai"

# Target Categories
categories:
  - "BASMATI"
  - "SELLA"
  - "JASMINE"

# Retry Settings
retry:
  max_attempts: 3
  delay_seconds: 2
  backoff_multiplier: 2

# Output Settings
output:
  csv_enabled: true
  excel_enabled: true
  output_dir: "output"
```

## Usage

### Basic Usage - Scrape All Retailers and Countries

```bash
python main.py
```

### Scrape Specific Retailer

```bash
# Scrape only Carrefour
python main.py --retailer carrefour

# Scrape only Lulu
python main.py --retailer lulu
```

### Scrape Specific Country

```bash
# Scrape only UAE
python main.py --country uae

# Scrape only KSA
python main.py --country ksa
```

### Combine Filters

```bash
# Scrape Carrefour in UAE only
python main.py --retailer carrefour --country uae
```

### Export Options

```bash
# Export only to CSV
python main.py --csv-only

# Export only to Excel
python main.py --excel-only

# Custom output filename
python main.py --output my_rice_data
```

### Verbose Logging

```bash
python main.py --verbose
```

### Help

```bash
python main.py --help
```

## Output Files

### Individual Files
Generated in the `output/` directory:
- `rice_prices_YYYYMMDD_HHMMSS_carrefour_uae.csv`
- `rice_prices_YYYYMMDD_HHMMSS_carrefour_uae.xlsx`
- `rice_prices_YYYYMMDD_HHMMSS_carrefour_ksa.csv`
- `rice_prices_YYYYMMDD_HHMMSS_carrefour_ksa.xlsx`
- `rice_prices_YYYYMMDD_HHMMSS_lulu_uae.csv`
- `rice_prices_YYYYMMDD_HHMMSS_lulu_uae.xlsx`
- `rice_prices_YYYYMMDD_HHMMSS_lulu_ksa.csv`
- `rice_prices_YYYYMMDD_HHMMSS_lulu_ksa.xlsx`

### Combined File
- `rice_prices_combined_YYYYMMDD_HHMMSS.csv`
- `rice_prices_combined_YYYYMMDD_HHMMSS.xlsx` (with separate sheets by retailer and country)

## Data Schema

Each exported file contains the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `product_name` | Full product name | "India Gate Basmati Rice 5kg" |
| `pack_size` | Extracted pack size | "5kg" |
| `currency` | Price currency | "AED" or "SAR" |
| `regular_price` | Regular price | 45.50 |
| `promo_price` | Promotional price (if any) | 39.99 or null |
| `is_promo` | Whether product is on promotion | true/false |
| `availability` | Stock status | "In Stock" or "Out of Stock" |
| `product_url` | Direct product link | "https://..." |
| `retailer` | Retailer name | "Carrefour" or "Lulu" |
| `country` | Country code | "UAE" or "KSA" |
| `category` | Rice category | "BASMATI" or "JASMINE" |
| `scraped_at` | Timestamp of scraping | "2026-02-05T09:00:00" |

## Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_utils

# Run with verbose output
python -m unittest discover tests -v
```

## Scheduling (Monday 9 AM Dubai Time)

### Option 1: Windows Task Scheduler

1. Open Task Scheduler
2. Create a new task
3. Set trigger: Weekly, Monday, 9:00 AM
4. Set action: Start program `python.exe`
5. Add arguments: `"path\to\main.py"`
6. Set start in: `"path\to\Code_v1"`

### Option 2: Python Scheduling Script

Create a `scheduler.py`:

```python
import schedule
import time
import subprocess
from datetime import datetime
import pytz

def run_scraper():
    """Run the rice price scraper."""
    print(f"Starting scraper at {datetime.now()}")
    subprocess.run(["python", "main.py"])

# Schedule for Monday 9 AM Dubai time
schedule.every().monday.at("09:00").do(run_scraper)

while True:
    schedule.run_pending()
    time.sleep(60)
```

Run continuously:
```bash
python scheduler.py
```

## Logging

Logs are saved to `logs/scraper.log` with the following levels:
- **INFO**: General progress and status
- **WARNING**: Recoverable issues
- **ERROR**: Critical failures
- **DEBUG**: Detailed debugging (use `--verbose` flag)

## Troubleshooting

### Playwright Installation Issues

```bash
# Reinstall Playwright
pip uninstall playwright
pip install playwright
playwright install chromium
```

### SSL Certificate Errors

Add to your script:
```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### Rate Limiting

Adjust retry settings in [config.yaml](config.yaml):
```yaml
retry:
  max_attempts: 5
  delay_seconds: 5
  backoff_multiplier: 3
```

## Notes

- **Carrefour API**: The actual API endpoint structure may vary. Inspect network traffic using browser DevTools to find the correct endpoints.
- **Lulu Selectors**: CSS selectors may change over time. Update selectors in [lulu_scraper.py](src/scrapers/lulu_scraper.py) if scraping fails.
- **Rate Limiting**: Be respectful of website resources. The scraper includes retry logic with delays.
- **Terms of Service**: Ensure compliance with website terms of service before scraping.

## License

This project is for educational and research purposes only.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Contact

For issues or questions, please open an issue in the repository.

---

**Happy Scraping! 🍚**
