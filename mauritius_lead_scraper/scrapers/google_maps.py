"""Scraper for Google Maps business listings in Mauritius."""

import logging
import re
import json
from typing import Optional

from mauritius_lead_scraper.models import Lead
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GoogleMapsScraper(BaseScraper):
    """
    Scrape business leads from Google Maps for Mauritius.

    Uses the Google Places API (requires API key) or falls back to
    web scraping of Google Maps search results.
    """

    PLACES_API_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key

    @property
    def source_name(self) -> str:
        return "Google Maps"

    def scrape(
        self,
        category: Optional[str] = None,
        district: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100,
    ) -> list[Lead]:
        """Scrape leads from Google Maps for Mauritius."""
        self.leads = []

        if self.api_key:
            return self._scrape_with_api(category, district, query, max_results)

        return self._scrape_web(category, district, query, max_results)

    def _scrape_with_api(
        self,
        category: Optional[str],
        district: Optional[str],
        query: Optional[str],
        max_results: int,
    ) -> list[Lead]:
        """Scrape using Google Places API."""
        search_query = self._build_query(category, district, query)
        logger.info("Searching Google Places API for: %s", search_query)

        url = f"{self.PLACES_API_URL}/textsearch/json"
        params = {
            "query": search_query,
            "key": self.api_key,
        }

        next_page_token = None
        while len(self.leads) < max_results:
            if next_page_token:
                params["pagetoken"] = next_page_token

            data = self.fetch_json(url, params=params)
            if not data or data.get("status") != "OK":
                error = data.get("status", "Unknown") if data else "No response"
                logger.error("Google Places API error: %s", error)
                break

            for result in data.get("results", []):
                lead = self._parse_api_result(result, category)
                if lead:
                    self.leads.append(lead)
                if len(self.leads) >= max_results:
                    break

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

        # Fetch details for each place to get phone/email/website
        detailed_leads = []
        for lead in self.leads[:max_results]:
            if hasattr(lead, "_place_id") and lead._place_id:
                detailed = self._fetch_place_details(lead._place_id, lead)
                detailed_leads.append(detailed)
            else:
                detailed_leads.append(lead)

        self.leads = detailed_leads
        logger.info("Found %d leads from Google Maps API", len(self.leads))
        return self.get_results()

    def _scrape_web(
        self,
        category: Optional[str],
        district: Optional[str],
        query: Optional[str],
        max_results: int,
    ) -> list[Lead]:
        """Scrape Google Maps via web search (no API key needed)."""
        search_query = self._build_query(category, district, query)
        logger.info("Searching Google Maps web for: %s", search_query)

        search_url = "https://www.google.com/search"
        params = {
            "q": f"{search_query} site:google.com/maps",
            "num": min(max_results, 20),
        }

        soup = self.fetch_page(search_url, params=params)
        if not soup:
            logger.warning("Could not fetch Google search results")
            return []

        # Parse search results for business information
        for result in soup.select(".g, [data-hveid]"):
            lead = self._parse_web_result(result, category, district)
            if lead and lead.is_complete():
                self.leads.append(lead)
            if len(self.leads) >= max_results:
                break

        logger.info("Found %d leads from Google Maps web", len(self.leads))
        return self.get_results()

    def _build_query(
        self,
        category: Optional[str],
        district: Optional[str],
        query: Optional[str],
    ) -> str:
        """Build a search query for Mauritius businesses."""
        parts = []
        if query:
            parts.append(query)
        if category:
            parts.append(category)
        if district:
            parts.append(district)
        parts.append("Mauritius")
        return " ".join(parts)

    def _parse_api_result(self, result: dict, category: Optional[str]) -> Optional[Lead]:
        """Parse a Google Places API result into a Lead."""
        try:
            name = result.get("name")
            if not name:
                return None

            lead = Lead(
                name=name,
                address=result.get("formatted_address"),
                category=category or ", ".join(result.get("types", [])),
                source=self.source_name,
            )

            # Store place_id for detail lookup
            lead._place_id = result.get("place_id")
            return lead
        except Exception as e:
            logger.debug("Failed to parse API result: %s", e)
            return None

    def _fetch_place_details(self, place_id: str, lead: Lead) -> Lead:
        """Fetch detailed info (phone, website) for a place."""
        url = f"{self.PLACES_API_URL}/details/json"
        params = {
            "place_id": place_id,
            "fields": "formatted_phone_number,international_phone_number,website,url",
            "key": self.api_key,
        }

        data = self.fetch_json(url, params=params)
        if data and data.get("status") == "OK":
            details = data.get("result", {})
            lead.phone = details.get("international_phone_number") or details.get(
                "formatted_phone_number"
            )
            lead.website = details.get("website")

        return lead

    def _parse_web_result(
        self, result, category: Optional[str], district: Optional[str]
    ) -> Optional[Lead]:
        """Parse a web search result into a Lead."""
        try:
            title_el = result.select_one("h3")
            if not title_el:
                return None

            name = title_el.get_text(strip=True)
            # Clean up Google search artifacts from name
            name = re.sub(r"\s*-\s*Google Maps.*$", "", name)
            if not name or "google" in name.lower():
                return None

            # Try to extract phone from snippet
            phone = None
            snippet = result.get_text()
            phone_match = re.search(r"(\+230\s?\d{3,4}\s?\d{4}|\d{3,4}\s?\d{4})", snippet)
            if phone_match:
                phone = re.sub(r"\s", "", phone_match.group())

            # Try to extract address
            address = None
            addr_match = re.search(
                r"(\d+[^,]*,\s*(?:Port Louis|Quatre Bornes|Rose Hill|Curepipe|Vacoas|Beau Bassin|Phoenix|Ebene|Moka|Flic en Flac|Grand Baie|Mahebourg)[^.]*)",
                snippet,
                re.IGNORECASE,
            )
            if addr_match:
                address = addr_match.group(1).strip()

            return Lead(
                name=name,
                phone=phone,
                address=address,
                district=district,
                category=category,
                source=self.source_name,
            )
        except Exception as e:
            logger.debug("Failed to parse web result: %s", e)
            return None
