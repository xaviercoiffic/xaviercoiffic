"""Command-line interface for the Mauritius Lead Scraper."""

import argparse
import logging
import sys
from typing import Optional

from mauritius_lead_scraper import __version__
from mauritius_lead_scraper.models import (
    Lead,
    MAURITIUS_DISTRICTS,
    BUSINESS_CATEGORIES,
)
from mauritius_lead_scraper.scrapers import (
    YellowPagesScraper,
    GoogleMapsScraper,
    BusinessDirectoryScraper,
)
from mauritius_lead_scraper.exporters import export_csv, export_json, export_excel


SCRAPERS = {
    "yellowpages": YellowPagesScraper,
    "google": GoogleMapsScraper,
    "directories": BusinessDirectoryScraper,
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mauritius-leads",
        description="Mauritius Lead Scraper - Generate business leads from Mauritius directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mauritius-leads search --query "restaurant" --district "Port Louis"
  mauritius-leads search --category "Hotels" --source yellowpages --output leads.csv
  mauritius-leads search --query "IT services" --format json --max 50
  mauritius-leads categories
  mauritius-leads districts
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for business leads")
    search_parser.add_argument(
        "-q", "--query", type=str, help="Search query (e.g., 'restaurant', 'IT company')"
    )
    search_parser.add_argument(
        "-c", "--category", type=str, help="Business category to search"
    )
    search_parser.add_argument(
        "-d",
        "--district",
        type=str,
        choices=MAURITIUS_DISTRICTS,
        help="Filter by Mauritius district",
    )
    search_parser.add_argument(
        "-s",
        "--source",
        type=str,
        choices=list(SCRAPERS.keys()) + ["all"],
        default="all",
        help="Data source to scrape (default: all)",
    )
    search_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="mauritius_leads",
        help="Output filename (default: mauritius_leads)",
    )
    search_parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["csv", "json", "excel", "all"],
        default="csv",
        help="Output format (default: csv)",
    )
    search_parser.add_argument(
        "-m",
        "--max",
        type=int,
        default=100,
        help="Maximum number of leads to scrape (default: 100)",
    )
    search_parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )
    search_parser.add_argument(
        "--google-api-key",
        type=str,
        help="Google Places API key (optional, enables richer Google Maps data)",
    )

    # Categories command
    subparsers.add_parser("categories", help="List available business categories")

    # Districts command
    subparsers.add_parser("districts", help="List Mauritius districts")

    return parser


def run_search(args) -> list[Lead]:
    """Execute the search based on CLI arguments."""
    if not args.query and not args.category:
        print("Error: Please provide --query or --category")
        sys.exit(1)

    all_leads: list[Lead] = []
    sources = list(SCRAPERS.keys()) if args.source == "all" else [args.source]

    for source_name in sources:
        scraper_class = SCRAPERS[source_name]
        kwargs = {"delay": args.delay}

        if source_name == "google" and args.google_api_key:
            kwargs["api_key"] = args.google_api_key

        scraper = scraper_class(**kwargs)
        print(f"Scraping {scraper.source_name}...")

        try:
            leads = scraper.scrape(
                category=args.category,
                district=args.district,
                query=args.query,
                max_results=args.max,
            )
            all_leads.extend(leads)
            print(f"  Found {len(leads)} leads from {scraper.source_name}")
        except Exception as e:
            print(f"  Error scraping {scraper.source_name}: {e}")
            logging.exception("Scraper error")

    # Deduplicate across sources
    seen = set()
    unique_leads = []
    for lead in all_leads:
        key = (lead.name.lower().strip(), (lead.phone or "").strip())
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)

    print(f"\nTotal unique leads: {len(unique_leads)}")
    return unique_leads


def export_leads(leads: list[Lead], args):
    """Export leads to the specified format(s)."""
    if not leads:
        print("No leads to export.")
        return

    formats = ["csv", "json", "excel"] if args.format == "all" else [args.format]
    output_base = args.output

    for fmt in formats:
        try:
            if fmt == "csv":
                path = export_csv(leads, output_base)
            elif fmt == "json":
                path = export_json(leads, output_base)
            elif fmt == "excel":
                path = export_excel(leads, output_base)
            else:
                continue
            print(f"Exported to: {path}")
        except ImportError as e:
            print(f"Export error ({fmt}): {e}")
        except Exception as e:
            print(f"Export error ({fmt}): {e}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "search":
        leads = run_search(args)
        export_leads(leads, args)
    elif args.command == "categories":
        print("Available business categories in Mauritius:")
        print("-" * 40)
        for cat in BUSINESS_CATEGORIES:
            print(f"  {cat}")
    elif args.command == "districts":
        print("Mauritius districts:")
        print("-" * 40)
        for district in MAURITIUS_DISTRICTS:
            print(f"  {district}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
