"""Scraper for Mauritius business directories (mauritiusdirectory.org, etc.)."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

from mauritius_lead_scraper.models import Lead
from .base import BaseScraper

logger = logging.getLogger(__name__)


class BusinessDirectoryScraper(BaseScraper):
    """Scrape leads from various Mauritius online business directories."""

    DIRECTORIES = [
        {
            "name": "Mauritius Directory",
            "base_url": "https://www.mauritiusdirectory.org",
            "search_path": "/search",
            "query_param": "q",
        },
        {
            "name": "Mauritius Business",
            "base_url": "https://www.mauritius-business.com",
            "search_path": "/search",
            "query_param": "keyword",
        },
        {
            "name": "Komkom",
            "base_url": "https://www.komkom.mu",
            "search_path": "/search",
            "query_param": "q",
        },
    ]

    @property
    def source_name(self) -> str:
        return "Business Directories"

    def scrape(
        self,
        category: Optional[str] = None,
        district: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100,
    ) -> list[Lead]:
        """Scrape leads from multiple Mauritius business directories."""
        self.leads = []
        search_term = query or category or "business"

        for directory in self.DIRECTORIES:
            if len(self.leads) >= max_results:
                break

            remaining = max_results - len(self.leads)
            leads = self._scrape_directory(
                directory, search_term, district, remaining
            )
            for lead in leads:
                lead.category = category or lead.category
                if district:
                    lead.district = district
            self.leads.extend(leads)

        logger.info("Found %d total leads from business directories", len(self.leads))
        return self.get_results()

    def _scrape_directory(
        self,
        directory: dict,
        search_term: str,
        district: Optional[str],
        max_results: int,
    ) -> list[Lead]:
        """Scrape a single directory."""
        dir_name = directory["name"]
        base_url = directory["base_url"]
        logger.info("Searching %s for: %s", dir_name, search_term)

        leads = []
        page = 1

        while len(leads) < max_results:
            url = f"{base_url}{directory['search_path']}"
            params = {directory["query_param"]: search_term, "page": page}
            if district:
                params["location"] = district

            soup = self.fetch_page(url, params=params)
            if not soup:
                logger.warning("Could not fetch %s page %d", dir_name, page)
                break

            # Generic listing extraction - tries multiple common patterns
            listings = self._find_listings(soup)
            if not listings:
                logger.info("No listings found on %s page %d", dir_name, page)
                break

            for listing in listings:
                lead = self._parse_listing(listing, base_url)
                if lead:
                    lead.source = dir_name
                    leads.append(lead)

                if len(leads) >= max_results:
                    break

            # Check for next page
            next_link = soup.select_one(
                "a.next, .pagination .next, [rel='next'], a:contains('Next')"
            )
            if not next_link:
                break

            page += 1
            if page > 20:  # Safety limit
                break

        return leads

    def _find_listings(self, soup) -> list:
        """Find business listings using multiple CSS selector strategies."""
        selectors = [
            ".listing-item",
            ".business-listing",
            ".search-result",
            ".result-item",
            ".business-card",
            ".company-item",
            "[class*='listing']",
            "[class*='result']",
            "[itemtype='http://schema.org/LocalBusiness']",
            "[itemtype='https://schema.org/LocalBusiness']",
        ]

        for selector in selectors:
            listings = soup.select(selector)
            if listings:
                return listings

        # Fallback: look for repeated structural patterns
        # (e.g., divs with both a heading and contact info)
        candidates = []
        for div in soup.select("div, article, li"):
            has_heading = div.select_one("h2, h3, h4")
            has_contact = div.select_one(
                "[href^='tel:'], [href^='mailto:'], .phone, .tel"
            )
            if has_heading and has_contact:
                candidates.append(div)

        return candidates

    def _parse_listing(self, listing, base_url: str) -> Optional[Lead]:
        """Parse a listing element into a Lead."""
        try:
            # Name
            name_el = listing.select_one("h2, h3, h4, .name, [class*='name']")
            if not name_el:
                return None
            name = name_el.get_text(strip=True)
            if not name:
                return None

            # Phone
            phone = None
            phone_el = listing.select_one(
                "[href^='tel:'], .phone, .tel, [class*='phone']"
            )
            if phone_el:
                if phone_el.get("href", "").startswith("tel:"):
                    phone = phone_el["href"].replace("tel:", "").strip()
                else:
                    phone = phone_el.get_text(strip=True)
                phone = self._clean_phone(phone)

            # Email
            email = None
            email_el = listing.select_one("[href^='mailto:'], .email, [class*='email']")
            if email_el:
                if email_el.get("href", "").startswith("mailto:"):
                    email = email_el["href"].replace("mailto:", "").strip()
                else:
                    email = email_el.get_text(strip=True)
                # Validate email format
                if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    email = None

            # Address
            address = None
            addr_el = listing.select_one(
                ".address, [class*='address'], [class*='location'], address"
            )
            if addr_el:
                address = addr_el.get_text(strip=True)

            # Website
            website = None
            web_el = listing.select_one(
                ".website a, [class*='website'] a, [class*='url'] a"
            )
            if web_el:
                href = web_el.get("href", "")
                if href.startswith("http"):
                    website = href
                elif href.startswith("/"):
                    website = urljoin(base_url, href)

            # Category
            category = None
            cat_el = listing.select_one(
                ".category, [class*='category'], [class*='sector']"
            )
            if cat_el:
                category = cat_el.get_text(strip=True)

            # Description
            description = None
            desc_el = listing.select_one(
                ".description, [class*='desc'], p"
            )
            if desc_el:
                description = desc_el.get_text(strip=True)[:300]

            lead = Lead(
                name=name,
                phone=phone,
                email=email,
                website=website,
                address=address,
                category=category,
                description=description,
            )

            # Only return if we have at least a name
            return lead if name else None

        except Exception as e:
            logger.debug("Failed to parse listing: %s", e)
            return None

    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Clean and format Mauritius phone numbers."""
        cleaned = re.sub(r"[^\d+]", "", phone)
        if cleaned and not cleaned.startswith("+") and len(cleaned) == 7:
            cleaned = "+230" + cleaned
        return cleaned
