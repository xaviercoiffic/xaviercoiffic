"""Data models for leads and business information."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Lead:
    """Represents a business lead scraped from Mauritius directories."""

    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    # Mauritius-specific fields
    brn: Optional[str] = None  # Business Registration Number

    def to_dict(self) -> dict:
        return asdict(self)

    def is_complete(self) -> bool:
        """Check if the lead has minimum useful information."""
        return bool(self.name and (self.phone or self.email))

    def __str__(self) -> str:
        parts = [self.name]
        if self.phone:
            parts.append(f"Tel: {self.phone}")
        if self.email:
            parts.append(f"Email: {self.email}")
        if self.district:
            parts.append(f"District: {self.district}")
        return " | ".join(parts)


# Mauritius districts for validation and filtering
MAURITIUS_DISTRICTS = [
    "Black River",
    "Flacq",
    "Grand Port",
    "Moka",
    "Pamplemousses",
    "Plaines Wilhems",
    "Port Louis",
    "Riviere du Rempart",
    "Savanne",
    "Rodrigues",
]

# Common business categories in Mauritius
BUSINESS_CATEGORIES = [
    "Accommodation & Hotels",
    "Accounting & Finance",
    "Agriculture & Farming",
    "Automotive",
    "Banking & Insurance",
    "Beauty & Wellness",
    "Construction & Real Estate",
    "Education & Training",
    "Electronics & IT",
    "Food & Beverages",
    "Healthcare & Medical",
    "Import & Export",
    "Legal Services",
    "Manufacturing",
    "Marine & Fishing",
    "Media & Advertising",
    "Offshore & BPO",
    "Restaurants & Catering",
    "Retail & Shopping",
    "Sugar Industry",
    "Telecommunications",
    "Textile & Garments",
    "Tourism & Travel",
    "Transport & Logistics",
]
