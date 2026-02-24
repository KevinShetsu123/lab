"""Scrapper service package."""

from backend.services.scrappers.base import BaseScraper
from backend.services.scrappers.cafef import CafeFScraper

__all__ = [
    "BaseScraper",
    "CafeFScraper"
]
