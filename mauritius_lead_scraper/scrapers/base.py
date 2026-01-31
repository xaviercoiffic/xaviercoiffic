"""Base scraper with shared functionality for all Mauritius scrapers."""

import logging
import time
import random
from abc import ABC, abstractmethod
from typing import Optional

import requests
from bs4 import BeautifulSoup

from mauritius_lead_scraper.models import Lead

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all Mauritius lead scrapers."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, delay: float = 2.0, max_retries: int = 3):
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": random.choice(self.USER_AGENTS)})
        self.leads: list[Lead] = []

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source."""
        ...

    @abstractmethod
    def scrape(
        self,
        category: Optional[str] = None,
        district: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100,
    ) -> list[Lead]:
        """Scrape leads from the source."""
        ...

    def fetch_page(self, url: str, params: Optional[dict] = None) -> Optional[BeautifulSoup]:
        """Fetch a page with retry logic and polite delays."""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay + random.uniform(0.5, 1.5))
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return BeautifulSoup(response.text, "html.parser")
            except requests.RequestException as e:
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self.max_retries,
                    url,
                    e,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
        logger.error("All retries failed for %s", url)
        return None

    def fetch_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Fetch JSON data with retry logic."""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.delay + random.uniform(0.5, 1.5))
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as e:
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self.max_retries,
                    url,
                    e,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
        logger.error("All retries failed for %s", url)
        return None

    def deduplicate(self, leads: list[Lead]) -> list[Lead]:
        """Remove duplicate leads based on name and phone."""
        seen = set()
        unique = []
        for lead in leads:
            key = (lead.name.lower().strip(), (lead.phone or "").strip())
            if key not in seen:
                seen.add(key)
                unique.append(lead)
        return unique

    def get_results(self) -> list[Lead]:
        """Return deduplicated leads."""
        return self.deduplicate(self.leads)
