# Mauritius Lead Scraper

A Python-based lead generation tool specialized for scraping business information from Mauritius directories and search engines.

## Features

- **Multiple Sources**: Scrapes from Yellow Pages Mauritius, Google Maps, and local business directories
- **Mauritius-Specific**: Built-in knowledge of Mauritius districts, business categories, and phone number formats (+230)
- **Flexible Export**: Export leads to CSV, JSON, or Excel formats
- **Smart Deduplication**: Automatically removes duplicate leads across sources
- **Polite Scraping**: Configurable delays and retry logic to respect rate limits
- **Google Places API Support**: Optional API key integration for richer Google Maps data

## Installation

```bash
# Clone the repository
git clone https://github.com/xaviercoiffic/xaviercoiffic.git
cd xaviercoiffic

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Usage

### Search for leads

```bash
# Search by query
mauritius-leads search --query "restaurant" --district "Port Louis"

# Search by category
mauritius-leads search --category "Hotels" --source yellowpages --output leads.csv

# Search with multiple options
mauritius-leads search --query "IT services" --format json --max 50

# Export to all formats
mauritius-leads search --query "accounting" --format all --output my_leads

# Use Google Places API for richer data
mauritius-leads search --query "hotel" --source google --google-api-key YOUR_KEY
```

### List categories and districts

```bash
# View available business categories
mauritius-leads categories

# View Mauritius districts
mauritius-leads districts
```

### Use as a Python library

```python
from mauritius_lead_scraper.scrapers import YellowPagesScraper, GoogleMapsScraper
from mauritius_lead_scraper.exporters import export_csv, export_json

# Scrape Yellow Pages
scraper = YellowPagesScraper(delay=2.0)
leads = scraper.scrape(query="restaurant", district="Port Louis", max_results=50)

# Export results
export_csv(leads, "restaurants.csv")
export_json(leads, "restaurants.json")

# Use Google Maps with API key
gmap = GoogleMapsScraper(api_key="YOUR_API_KEY")
leads = gmap.scrape(category="Hotels", max_results=30)
```

## Data Sources

| Source | Description | API Key Required |
|--------|-------------|-----------------|
| Yellow Pages Mauritius | yellowpages.mu business listings | No |
| Google Maps | Google Maps business search | Optional (enhances results) |
| Business Directories | Multiple Mauritius directories (mauritiusdirectory.org, komkom.mu, etc.) | No |

## Mauritius Districts

- Black River
- Flacq
- Grand Port
- Moka
- Pamplemousses
- Plaines Wilhems
- Port Louis
- Riviere du Rempart
- Savanne
- Rodrigues

## Output Format

Each lead contains:

| Field | Description |
|-------|-------------|
| `name` | Business name |
| `phone` | Phone number (formatted with +230 prefix) |
| `email` | Email address |
| `website` | Business website URL |
| `address` | Physical address |
| `district` | Mauritius district |
| `category` | Business category |
| `description` | Short business description |
| `brn` | Business Registration Number |
| `source` | Data source name |
| `tags` | Additional tags |

## Configuration

### Request Delays

Use `--delay` to set the time between requests (default: 2 seconds):

```bash
mauritius-leads search --query "shops" --delay 3.0
```

### Verbose Logging

Enable debug output with `-v`:

```bash
mauritius-leads search --query "banks" -v
```

## Project Structure

```
mauritius_lead_scraper/
├── __init__.py          # Package metadata
├── cli.py               # Command-line interface
├── models.py            # Lead data model & Mauritius constants
├── exporters.py         # CSV, JSON, Excel export
└── scrapers/
    ├── __init__.py
    ├── base.py              # Base scraper with retry logic
    ├── yellow_pages.py      # Yellow Pages Mauritius scraper
    ├── google_maps.py       # Google Maps scraper (API + web)
    └── business_directory.py # Multi-directory scraper
```

## License

MIT

## Author

Xavier Coiffic - hi@xavier.mu
