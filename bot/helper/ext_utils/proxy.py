#!/usr/bin/env python3
from __future__ import annotations

from itertools import cycle
from random import choice
from threading import Lock
from typing import Dict, Optional

from bot import config_dict


class RotatingProxyManager:
    """Provides rotating proxies for requests, aiohttp, and yt-dlp.

    Supports rotation modes: off, round_robin, random.
    """

    def __init__(self, proxies_csv: str, mode: str = "off") -> None:
        self._lock = Lock()
        self._raw_list = self._parse_list(proxies_csv)
        self._mode = mode or "off"
        self._cycler = cycle(self._raw_list) if self._raw_list else None

    @staticmethod
    def _normalize(proxy: str) -> str:
        proxy = proxy.strip()
        if not proxy:
            return ""
        if "://" not in proxy:
            # default to http
            proxy = f"http://{proxy}"
        return proxy

    def _parse_list(self, proxies_csv: str) -> list[str]:
        if not proxies_csv:
            return []
        items = [self._normalize(p) for p in proxies_csv.split(",")]
        return [p for p in items if p]

    def get_requests_proxies(self) -> Optional[Dict[str, str]]:
        proxy = self._pick()
        if not proxy:
            return None
        return {
            "http": proxy,
            "https": proxy,
        }

    def get_aiohttp_proxy(self) -> Optional[str]:
        return self._pick()

    def _pick(self) -> Optional[str]:
        if not self._raw_list:
            return None
        with self._lock:
            if self._mode == "off":
                return None
            if self._mode == "random":
                return choice(self._raw_list)
            # round_robin
            return next(self._cycler)


# Singleton configured from env/config
_proxy_manager = RotatingProxyManager(
    config_dict.get("PROXIES", ""), config_dict.get("PROXY_ROTATE_MODE", "off")
)


def next_requests_proxies() -> Optional[Dict[str, str]]:
    return _proxy_manager.get_requests_proxies()


def next_aiohttp_proxy() -> Optional[str]:
    return _proxy_manager.get_aiohttp_proxy()


def with_cloudscraper_proxies():
    """Return kwargs to pass into cloudscraper.create_scraper for proxies."""
    proxies = _proxy_manager.get_requests_proxies()
    return {"proxies": proxies} if proxies else {}
