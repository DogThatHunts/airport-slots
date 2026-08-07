"""Common scraper interface.

Every source implements Scraper.fetch() -> list[dict], using its dataset's field
names (see src/schema.py). Keep scrapers focused on fetch + parse; provenance and
row keys are added downstream in normalize.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

# Some coordinator sites 403 non-browser agents; present a realistic one.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 airport-slots-bot/0.1")


@dataclass
class Scraper:
    key: str
    url: str
    fmt: str = "unknown"
    opts: dict[str, Any] = field(default_factory=dict)

    def get(self, url: str | None = None, **kw) -> requests.Response:
        resp = requests.get(url or self.url, headers={"User-Agent": USER_AGENT},
                            timeout=60, **kw)
        resp.raise_for_status()
        return resp

    def fetch(self) -> list[dict]:
        raise NotImplementedError(f"{self.key}: fetch() not implemented yet")


def load(key: str, url: str, fmt: str, opts: dict | None = None) -> Scraper:
    """Registry hook. Import and return the concrete scraper for `key`."""
    if key == "iata_wasg":
        from .iata_wasg import IataWasgScraper
        return IataWasgScraper(key=key, url=url, fmt=fmt, opts=opts or {})
    if key == "anac_br":
        from .anac_br import AnacBrScraper
        return AnacBrScraper(key=key, url=url, fmt=fmt, opts=opts or {})
    raise KeyError(f"No scraper registered for source '{key}'")
