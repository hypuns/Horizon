"""TianAPI financial news scraper."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

import httpx
from dateutil import parser as date_parser

from .base import BaseScraper
from ..models import ContentItem, SourceType, TianAPIConfig, TianAPIChannelConfig

logger = logging.getLogger(__name__)


class TianAPIScraper(BaseScraper):
    """Scrape TianAPI finance/news endpoints into Horizon content items."""

    SOURCE_TYPE = SourceType.TIANAPI

    def __init__(self, config: TianAPIConfig, http_client: httpx.AsyncClient):
        super().__init__({"tianapi": config}, http_client)
        self.tianapi_config = config

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.tianapi_config.enabled:
            return []

        api_key = os.getenv(self.tianapi_config.api_key_env, "").strip()
        if not api_key:
            logger.warning(
                "TianAPI source is enabled but %s is not set",
                self.tianapi_config.api_key_env,
            )
            return []

        items: List[ContentItem] = []
        for channel in self.tianapi_config.channels:
            if not channel.enabled:
                continue
            items.extend(await self._fetch_channel(channel, api_key, since))
        return items

    async def _fetch_channel(
        self, channel: TianAPIChannelConfig, api_key: str, since: datetime
    ) -> List[ContentItem]:
        params: dict[str, Any] = {
            "key": api_key,
            "num": channel.num,
            "page": channel.page,
        }
        if channel.word:
            params["word"] = channel.word
        if channel.urlid is not None:
            params["urlid"] = channel.urlid

        try:
            response = await self.client.get(
                channel.endpoint, params=params, follow_redirects=True
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Error fetching TianAPI channel %s: %s", channel.name, exc)
            return []
        except ValueError as exc:
            logger.warning("Invalid TianAPI JSON for channel %s: %s", channel.name, exc)
            return []

        if int(payload.get("code", 0) or 0) != 200:
            logger.warning(
                "TianAPI channel %s returned code=%s msg=%s",
                channel.name,
                payload.get("code"),
                payload.get("msg"),
            )
            return []

        news_items = self._extract_news_list(payload)
        results: List[ContentItem] = []
        since_utc = self._ensure_utc(since)
        for raw in news_items:
            item = self._to_content_item(raw, channel)
            if item and item.published_at >= since_utc:
                results.append(item)
        return results

    @staticmethod
    def _extract_news_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        result = payload.get("result")
        if isinstance(result, dict):
            for key in ("newslist", "list", "data"):
                value = result.get(key)
                if isinstance(value, list):
                    return [entry for entry in value if isinstance(entry, dict)]
        newslist = payload.get("newslist")
        if isinstance(newslist, list):
            return [entry for entry in newslist if isinstance(entry, dict)]
        return []

    def _to_content_item(
        self, raw: dict[str, Any], channel: TianAPIChannelConfig
    ) -> Optional[ContentItem]:
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        if not title or not url:
            return None

        published = self._parse_datetime(raw.get("ctime") or raw.get("time"))
        if published is None:
            return None

        native_id = str(raw.get("id") or url)
        digest = hashlib.sha256(native_id.encode("utf-8")).hexdigest()[:16]
        source_name = str(raw.get("source") or channel.name).strip()
        description = str(raw.get("description") or "").strip() or None

        metadata = {
            "category": channel.category,
            "channel": channel.name,
            "source_name": source_name,
            "pic_url": raw.get("picUrl"),
        }

        return ContentItem(
            id=self._generate_id("tianapi", "news", digest),
            source_type=self.SOURCE_TYPE,
            title=title,
            url=url,
            content=description,
            author=source_name,
            published_at=published,
            profile=channel.profile,
            metadata={k: v for k, v in metadata.items() if v},
        )

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = date_parser.parse(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _ensure_utc(moment: datetime) -> datetime:
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
