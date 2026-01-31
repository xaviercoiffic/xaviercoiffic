"""Scraper for Yellow Pages Mauritius (yellowy.mu / yellow.mu)."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

from mauritius_lead_scraper.models import Lead
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.yellowpages.mu"


class YellowPagesScraper(BaseScraper):
    """Scrape business leads from Yellow Pages Mauritius."""

    @property
    def source_name(self) -> str:
        return "Yellow Pages Mauritius"

    def scrape(
        self,
        category: Optional[str] = None,
        district: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100,
    ) -> list[Lead]:
        """Scrape leads from Yellow Pages Mauritius."""
        self.leads = []
        search_term = query or category or "business"
        logger.info("Searching Yellow Pages Mauritius for: %s", search_term)

        page = 1
        while len(self.leads) < max_results:
            url = f"{BASE_URL}/search"
            params = {"q": search_term, "page": page}
            if district:
                params["location"] = district

            soup = self.fetch_page(url, params=params)
            if not soup:
                break

            listings = soup.select(".listing-item, .search-result, .business-card")
            if not listings:
                # Try alternative selectors
                listings = soup.select("[class*='listing'], [class*='result']")

            if not listings:
                logger.info("No more results found on page %d", page)
                break

            for listing in listings:
                lead = self._parse_listing(listing)
                if lead and lead.is_complete():
                    lead.source = self.source_name
                    if category:
                        lead.category = category
                    if district:
                        lead.district = district
                    self.leads.append(lead)

                if len(self.leads) >= max_results:
                    break

            page += 1
            if page > 50:  # Safety limit
                break

        logger.info("Found %d leads from Yellow Pages", len(self.leads))
        return self.get_results()

    def _parse_listing(self, listing) -> Optional[Lead]:
        """Parse a single listing into a Lead."""
        try:
            # Extract business name
            name_el = listing.select_one(
                "h2, h3, .business-name, .listing-name, [class*='name']"
            )
            if not name_el:
                return None
            name = name_el.get_text(strip=True)
            if not name:
                return None

            # Extract phone number
            phone = None
            phone_el = listing.select_one(
                ".phone, .tel, [class*='phone'], [href^='tel:']"
            )
            if phone_el:
                if phone_el.get("href", "").startswith("tel:"):
                    phone = phone_el["href"].replace("tel:", "").strip()
                else:
                    phone = phone_el.get_text(strip=True)
            if phone:
                phone = self._clean_phone(phone)

            # Extract email
            email = None
            email_el = listing.select_one("[href^='mailto:'], .email")
            if email_el:
                if email_el.get("href", "").startswith("mailto:"):
                    email = email_el["href"].replace("mailto:", "").strip()
                else:
                    email = email_el.get_text(strip=True)

            # Extract address
            address = None
            addr_el = listing.select_one(
                ".address, .location, [class*='address'], [class*='location']"
            )
            if addr_el:
                address = addr_el.get_text(strip=True)

            # Extract website
            website = None
            web_el = listing.select_one(".website a, [class*='website'] a")
            if web_el:
                website = web_el.get("href")

            # Extract category
            cat = None
            cat_el = listing.select_one(".category, [class*='category']")
            if cat_el:
                cat = cat_el.get_text(strip=True)

            return Lead(
                name=name,
                phone=phone,
                email=email,
                website=website,
                address=address,
                category=cat,
            )
        except Exception as e:
            logger.debug("Failed to parse listing: %s", e)
            return None

    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Clean and format Mauritius phone numbers."""
        # Remove non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", phone)
        # Add Mauritius country code if missing
        if cleaned and not cleaned.startswith("+") and len(cleaned) == 7:
            cleaned = "+230" + cleaned
        return cleaned
