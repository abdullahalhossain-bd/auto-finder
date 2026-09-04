"""
Business Discovery Service

Sources:
- OpenStreetMap / Overpass as free seed source
- Optional Google Places API (paid, user-funded — opt-in only)

Features:
- Area search first
- Around-radius fallback
- Multiple Overpass endpoint fallback
- Proper HTTP headers
- Retry/backoff for transient failures
- Hard result limits
- Large-city timeout protection
- Sync API for Celery workers
- Async API for API/tests
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================
# OSM CATEGORY MAP
# ============================================================

OSM_CATEGORY_MAP: dict[str, list[str]] = {
    "barber": [
        '["shop"="hairdresser"]',
        '["shop"="barber"]',
    ],
    "hairdresser": [
        '["shop"="hairdresser"]',
        '["shop"="barber"]',
    ],
    "restaurant": [
        '["amenity"="restaurant"]',
    ],
    "cafe": [
        '["amenity"="cafe"]',
    ],
    "dentist": [
        '["amenity"="dentist"]',
    ],
    "doctor": [
        '["amenity"="doctors"]',
        '["amenity"="clinic"]',
    ],
    "plumber": [
        '["craft"="plumber"]',
    ],
    "electrician": [
        '["craft"="electrician"]',
    ],
    "gym": [
        '["leisure"="fitness_centre"]',
        '["leisure"="sports_centre"]',
    ],
    "hotel": [
        '["tourism"="hotel"]',
    ],
    "shop": [
        '["shop"]',
    ],
    "bakery": [
        '["shop"="bakery"]',
    ],
    "pharmacy": [
        '["amenity"="pharmacy"]',
    ],
    "lawyer": [
        '["office"="lawyer"]',
    ],
    "accountant": [
        '["office"="accountant"]',
    ],
}


# ============================================================
# CITY CENTERS
# ============================================================

CITY_CENTERS: dict[str, tuple[float, float, int]] = {
    "krakow": (50.0647, 19.9450, 12000),
    "kraków": (50.0647, 19.9450, 12000),
    "warsaw": (52.2297, 21.0122, 15000),
    "warszawa": (52.2297, 21.0122, 15000),
    "berlin": (52.5200, 13.4050, 15000),
    "london": (51.5074, -0.1278, 15000),
    "paris": (48.8566, 2.3522, 12000),
    "dhaka": (23.8103, 90.4125, 12000),
    "mumbai": (19.0760, 72.8777, 15000),
    "new york": (40.7128, -74.0060, 15000),
    "los angeles": (34.0522, -118.2437, 20000),
}


# ============================================================
# SERVICE
# ============================================================

class DiscoveryService:
    """Discover local businesses from public sources."""

    def __init__(self) -> None:
        # Primary endpoint from settings.
        primary_url = str(
            getattr(
                settings,
                "OVERPASS_API_URL",
                "https://overpass-api.de/api/interpreter",
            )
        ).strip()

        # Additional public Overpass endpoints.
        # Primary endpoint is always tried first.
        configured_fallbacks = getattr(
            settings,
            "OVERPASS_FALLBACK_URLS",
            "",
        )

        fallback_urls: list[str] = []

        if isinstance(configured_fallbacks, str):
            fallback_urls = [
                url.strip()
                for url in configured_fallbacks.split(",")
                if url.strip()
            ]
        elif isinstance(configured_fallbacks, (list, tuple)):
            fallback_urls = [
                str(url).strip()
                for url in configured_fallbacks
                if str(url).strip()
            ]

        # Built-in fallbacks.
        built_in_fallbacks = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
        ]

        self.overpass_urls: list[str] = []

        for url in [primary_url, *fallback_urls, *built_in_fallbacks]:
            if url and url not in self.overpass_urls:
                self.overpass_urls.append(url)

        # Keep compatibility with existing code.
        self.overpass_url = primary_url

        # Timeouts.
        self.query_timeout_sec = int(
            getattr(
                settings,
                "OVERPASS_QUERY_TIMEOUT_SEC",
                90,
            )
        )

        self.http_timeout_sec = float(
            getattr(
                settings,
                "OVERPASS_HTTP_TIMEOUT_SEC",
                100.0,
            )
        )

        # Result limits.
        self.default_limit = int(
            getattr(
                settings,
                "DISCOVERY_DEFAULT_LIMIT",
                50,
            )
        )

        self.max_limit = int(
            getattr(
                settings,
                "DISCOVERY_MAX_LIMIT",
                100,
            )
        )

        # Retry configuration.
        self.max_retries = int(
            getattr(
                settings,
                "OVERPASS_MAX_RETRIES",
                2,
            )
        )

        self.retry_delay_sec = float(
            getattr(
                settings,
                "OVERPASS_RETRY_DELAY_SEC",
                2.0,
            )
        )

        # HTTP headers.
        self.headers = {
            "User-Agent": (
                "AI-Sales-Agent/1.0 "
                "(OpenStreetMap discovery; business lead research)"
            ),
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        logger.info(
            "DiscoveryService initialized: endpoints=%s timeout=%ss "
            "query_timeout=%ss max_limit=%s",
            len(self.overpass_urls),
            self.http_timeout_sec,
            self.query_timeout_sec,
            self.max_limit,
        )

    # ========================================================
    # CATEGORY
    # ========================================================

    def _tag_selectors(self, business_type: str) -> list[str]:
        key = (business_type or "").lower().strip()

        return OSM_CATEGORY_MAP.get(
            key,
            [f'["shop"="{key}"]'],
        )

    # ========================================================
    # AREA QUERY
    # ========================================================

    def _build_area_query(
        self,
        city: str,
        business_type: str,
        country: Optional[str],
        limit: int,
    ) -> str:

        selectors = self._tag_selectors(business_type)

        node_parts: list[str] = []
        way_parts: list[str] = []

        for selector in selectors:
            node_parts.append(
                f"  node{selector}(area.searchArea);"
            )

            way_parts.append(
                f"  way{selector}(area.searchArea);"
            )

        elements = "\n".join(
            node_parts + way_parts
        )

        country_clause = (
            f'["is_in:country"="{country}"]'
            if country
            else ""
        )

        query = f"""
[out:json][timeout:{self.query_timeout_sec}];
(
  area["name"="{city}"]["admin_level"~"^(4|6|7|8|9|10)$"]{country_clause};
  area["name:en"="{city}"]["admin_level"~"^(4|6|7|8|9|10)$"]{country_clause};
)->.searchArea;

(
{elements}
);

out center tags {limit};
"""

        return query

    # ========================================================
    # AROUND QUERY
    # ========================================================

    def _build_around_query(
        self,
        lat: float,
        lon: float,
        radius_m: int,
        business_type: str,
        limit: int,
    ) -> str:

        selectors = self._tag_selectors(
            business_type
        )

        parts: list[str] = []

        for selector in selectors:
            parts.append(
                f"  node{selector}"
                f"(around:{radius_m},{lat},{lon});"
            )

            parts.append(
                f"  way{selector}"
                f"(around:{radius_m},{lat},{lon});"
            )

        elements = "\n".join(parts)

        return f"""
[out:json][timeout:{self.query_timeout_sec}];
(
{elements}
);

out center tags {limit};
"""

    # ========================================================
    # PARSER
    # ========================================================

    def _parse_elements(
        self,
        data: dict,
        business_type: str,
        limit: int,
    ) -> List[Dict[str, Any]]:

        results: List[Dict[str, Any]] = []

        if not isinstance(data, dict):
            logger.warning(
                "Invalid Overpass response type: %s",
                type(data).__name__,
            )
            return results

        elements = data.get("elements", [])

        if not isinstance(elements, list):
            return results

        for element in elements[:limit]:

            tags = element.get(
                "tags",
                {},
            ) or {}

            latitude = (
                element.get("lat")
                or (element.get("center") or {}).get("lat")
            )

            longitude = (
                element.get("lon")
                or (element.get("center") or {}).get("lon")
            )

            name = (
                tags.get("name")
                or tags.get("name:en")
                or "Unknown"
            )

            phone = (
                tags.get("phone")
                or tags.get("contact:phone")
            )

            website = (
                tags.get("website")
                or tags.get("contact:website")
                or tags.get("url")
            )

            results.append(
                {
                    "name": name,
                    "category": business_type,
                    "address": self._format_address(tags),
                    "latitude": latitude,
                    "longitude": longitude,
                    "phone": phone,
                    "website_url": website,

                    "source_data": {
                        "osm_id": element.get("id"),
                        "osm_type": element.get("type"),
                        "raw_tags": tags,
                        "source": "osm",
                    },

                    "confidence": {
                        "name": (
                            "likely"
                            if tags.get("name")
                            else "unknown"
                        ),
                        "phone": (
                            "likely"
                            if phone
                            else "unknown"
                        ),
                        "website": (
                            "likely"
                            if website
                            else "not_found"
                        ),
                        "address": (
                            "likely"
                            if tags.get("addr:street")
                            else "unknown"
                        ),
                    },
                }
            )

        return results

    # ========================================================
    # ADDRESS
    # ========================================================

    def _format_address(
        self,
        tags: dict,
    ) -> Optional[str]:

        parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city")
            or tags.get("addr:place"),
            tags.get("addr:postcode"),
        ]

        filtered = [
            part
            for part in parts
            if part
        ]

        return (
            ", ".join(filtered)
            if filtered
            else None
        )

    # ========================================================
    # SYNC OVERPASS REQUEST
    # ========================================================

    def _post_overpass_sync(
        self,
        query: str,
    ) -> dict:
        """
        Synchronous Overpass request.

        Used by Celery workers.

        Features:
        - Proper User-Agent
        - JSON Accept header
        - Retry
        - Multiple endpoints
        - Retryable HTTP status handling
        """

        last_error: Optional[Exception] = None

        for endpoint_index, endpoint in enumerate(
            self.overpass_urls,
            start=1,
        ):

            for attempt in range(
                self.max_retries + 1
            ):

                try:

                    logger.info(
                        "Overpass request endpoint=%s/%s "
                        "attempt=%s/%s url=%s",
                        endpoint_index,
                        len(self.overpass_urls),
                        attempt + 1,
                        self.max_retries + 1,
                        endpoint,
                    )

                    start_time = time.monotonic()

                    with httpx.Client(
                        timeout=self.http_timeout_sec,
                        headers=self.headers,
                        follow_redirects=True,
                    ) as client:

                        response = client.post(
                            endpoint,
                            data={"data": query},
                        )

                    elapsed = (
                        time.monotonic()
                        - start_time
                    )

                    logger.info(
                        "Overpass response "
                        "status=%s elapsed=%.2fs "
                        "endpoint=%s",
                        response.status_code,
                        elapsed,
                        endpoint,
                    )

                    # Success.
                    response.raise_for_status()

                    data = response.json()

                    if not isinstance(data, dict):
                        raise ValueError(
                            "Overpass returned invalid JSON object"
                        )

                    return data

                except httpx.HTTPStatusError as exc:

                    last_error = exc

                    status = (
                        exc.response.status_code
                        if exc.response
                        else None
                    )

                    logger.warning(
                        "Overpass HTTP error "
                        "status=%s endpoint=%s "
                        "attempt=%s: %s",
                        status,
                        endpoint,
                        attempt + 1,
                        exc,
                    )

                    # Retry transient/server/rate-limit errors.
                    retryable_statuses = {
                        408,
                        425,
                        429,
                        500,
                        502,
                        503,
                        504,
                    }

                    # 406 can happen because of endpoint/header
                    # negotiation. Try the next endpoint instead
                    # of wasting all retries on the same server.
                    if status == 406:
                        break

                    if (
                        status not in retryable_statuses
                        or attempt >= self.max_retries
                    ):
                        break

                    delay = (
                        self.retry_delay_sec
                        * (2 ** attempt)
                    )

                    logger.info(
                        "Retrying Overpass in %.1fs",
                        delay,
                    )

                    time.sleep(delay)

                except (
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    httpx.RequestError,
                ) as exc:

                    last_error = exc

                    logger.warning(
                        "Overpass network/timeout error "
                        "endpoint=%s attempt=%s: %s",
                        endpoint,
                        attempt + 1,
                        exc,
                    )

                    if attempt >= self.max_retries:
                        break

                    delay = (
                        self.retry_delay_sec
                        * (2 ** attempt)
                    )

                    logger.info(
                        "Retrying Overpass in %.1fs",
                        delay,
                    )

                    time.sleep(delay)

                except Exception as exc:

                    last_error = exc

                    logger.exception(
                        "Unexpected Overpass error "
                        "endpoint=%s attempt=%s",
                        endpoint,
                        attempt + 1,
                    )

                    break

        # Every endpoint failed.
        message = (
            "All Overpass endpoints failed"
        )

        if last_error:
            message += f": {last_error}"

        raise RuntimeError(message) from last_error

    # ========================================================
    # ASYNC OVERPASS REQUEST
    # ========================================================

    async def _post_overpass_async(
        self,
        query: str,
    ) -> dict:
        """
        Async Overpass request.

        Used by API/tests.
        """

        last_error: Optional[Exception] = None

        for endpoint_index, endpoint in enumerate(
            self.overpass_urls,
            start=1,
        ):

            for attempt in range(
                self.max_retries + 1
            ):

                try:

                    logger.info(
                        "Async Overpass request "
                        "endpoint=%s/%s attempt=%s/%s "
                        "url=%s",
                        endpoint_index,
                        len(self.overpass_urls),
                        attempt + 1,
                        self.max_retries + 1,
                        endpoint,
                    )

                    start_time = time.monotonic()

                    async with httpx.AsyncClient(
                        timeout=self.http_timeout_sec,
                        headers=self.headers,
                        follow_redirects=True,
                    ) as client:

                        response = await client.post(
                            endpoint,
                            data={"data": query},
                        )

                    elapsed = (
                        time.monotonic()
                        - start_time
                    )

                    logger.info(
                        "Async Overpass response "
                        "status=%s elapsed=%.2fs "
                        "endpoint=%s",
                        response.status_code,
                        elapsed,
                        endpoint,
                    )

                    response.raise_for_status()

                    data = response.json()

                    if not isinstance(data, dict):
                        raise ValueError(
                            "Overpass returned invalid JSON object"
                        )

                    return data

                except httpx.HTTPStatusError as exc:

                    last_error = exc

                    status = (
                        exc.response.status_code
                        if exc.response
                        else None
                    )

                    logger.warning(
                        "Async Overpass HTTP error "
                        "status=%s endpoint=%s "
                        "attempt=%s: %s",
                        status,
                        endpoint,
                        attempt + 1,
                        exc,
                    )

                    retryable_statuses = {
                        408,
                        425,
                        429,
                        500,
                        502,
                        503,
                        504,
                    }

                    if status == 406:
                        break

                    if (
                        status not in retryable_statuses
                        or attempt >= self.max_retries
                    ):
                        break

                    delay = (
                        self.retry_delay_sec
                        * (2 ** attempt)
                    )

                    await asyncio.sleep(delay)

                except (
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    httpx.RequestError,
                ) as exc:

                    last_error = exc

                    logger.warning(
                        "Async Overpass network/timeout "
                        "error endpoint=%s attempt=%s: %s",
                        endpoint,
                        attempt + 1,
                        exc,
                    )

                    if attempt >= self.max_retries:
                        break

                    delay = (
                        self.retry_delay_sec
                        * (2 ** attempt)
                    )

                    await asyncio.sleep(delay)

                except Exception as exc:

                    last_error = exc

                    logger.exception(
                        "Unexpected async Overpass error "
                        "endpoint=%s attempt=%s",
                        endpoint,
                        attempt + 1,
                    )

                    break

        message = (
            "All Overpass endpoints failed"
        )

        if last_error:
            message += f": {last_error}"

        raise RuntimeError(message) from last_error

    # ========================================================
    # SYNC OSM SEARCH
    # ========================================================

    def search_osm_sync(
        self,
        city: str,
        business_type: str,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Sync discovery for Celery.

        Flow:

        1. Area query
        2. Around-radius fallback
        3. Return structured error if provider fails
        """

        limit = max(
            1,
            min(
                limit or self.default_limit,
                self.max_limit,
            ),
        )

        city_clean = (
            city or ""
        ).strip()

        business_type_clean = (
            business_type or ""
        ).strip()

        if not city_clean or not business_type_clean:
            return [
                {
                    "error": (
                        "city and business_type "
                        "are required"
                    ),
                    "source": "overpass",
                    "error_type": "validation",
                }
            ]

        # ----------------------------------------------------
        # 1. AREA SEARCH
        # ----------------------------------------------------

        try:

            query = self._build_area_query(
                city_clean,
                business_type_clean,
                country,
                limit,
            )

            logger.info(
                "Overpass area query "
                "city=%s type=%s limit=%s",
                city_clean,
                business_type_clean,
                limit,
            )

            data = self._post_overpass_sync(
                query
            )

            results = self._parse_elements(
                data,
                business_type_clean,
                limit,
            )

            if results:
                logger.info(
                    "Overpass area discovery "
                    "found=%s city=%s type=%s",
                    len(results),
                    city_clean,
                    business_type_clean,
                )

                return results

            logger.warning(
                "Overpass area returned 0 "
                "elements for %s / %s; "
                "trying around fallback",
                city_clean,
                business_type_clean,
            )

        except Exception as exc:

            logger.warning(
                "Overpass area query failed "
                "city=%s type=%s: %s",
                city_clean,
                business_type_clean,
                exc,
            )

        # ----------------------------------------------------
        # 2. AROUND FALLBACK
        # ----------------------------------------------------

        center = CITY_CENTERS.get(
            city_clean.lower()
        )

        if not center:

            logger.error(
                "No fallback center for city=%s",
                city_clean,
            )

            return [
                {
                    "error": (
                        f"No results and no "
                        f"fallback center for "
                        f"city '{city_clean}'"
                    ),
                    "source": "overpass",
                    "error_type": "no_fallback",
                }
            ]

        lat, lon, radius = center

        try:

            query = self._build_around_query(
                lat,
                lon,
                radius,
                business_type_clean,
                limit,
            )

            logger.info(
                "Overpass around query "
                "lat=%s lon=%s r=%s "
                "type=%s limit=%s",
                lat,
                lon,
                radius,
                business_type_clean,
                limit,
            )

            data = self._post_overpass_sync(
                query
            )

            results = self._parse_elements(
                data,
                business_type_clean,
                limit,
            )

            logger.info(
                "Overpass around discovery "
                "found=%s city=%s type=%s",
                len(results),
                city_clean,
                business_type_clean,
            )

            return results

        except Exception as exc:

            logger.exception(
                "Overpass around query failed "
                "city=%s type=%s",
                city_clean,
                business_type_clean,
            )

            return [
                {
                    "error": str(exc),
                    "source": "overpass",
                    "error_type": "provider_failure",
                    "city": city_clean,
                    "business_type": business_type_clean,
                }
            ]

    # ========================================================
    # ASYNC OSM SEARCH
    # ========================================================

    async def search_osm(
        self,
        city: str,
        business_type: str,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Async discovery for API/tests.

        Flow:

        1. Area query
        2. Around fallback
        3. Structured provider error
        """

        limit = max(
            1,
            min(
                limit or self.default_limit,
                self.max_limit,
            ),
        )

        city_clean = (
            city or ""
        ).strip()

        business_type_clean = (
            business_type or ""
        ).strip()

        if not city_clean or not business_type_clean:
            return [
                {
                    "error": (
                        "city and business_type "
                        "are required"
                    ),
                    "source": "overpass",
                    "error_type": "validation",
                }
            ]

        # ----------------------------------------------------
        # 1. AREA SEARCH
        # ----------------------------------------------------

        try:

            query = self._build_area_query(
                city_clean,
                business_type_clean,
                country,
                limit,
            )

            logger.info(
                "Async Overpass area query "
                "city=%s type=%s limit=%s",
                city_clean,
                business_type_clean,
                limit,
            )

            data = await self._post_overpass_async(
                query
            )

            results = self._parse_elements(
                data,
                business_type_clean,
                limit,
            )

            if results:
                return results

            logger.warning(
                "Async Overpass area returned "
                "0 results; trying around fallback"
            )

        except Exception as exc:

            logger.warning(
                "Async Overpass area failed: %s",
                exc,
            )

        # ----------------------------------------------------
        # 2. AROUND FALLBACK
        # ----------------------------------------------------

        center = CITY_CENTERS.get(
            city_clean.lower()
        )

        if not center:

            return [
                {
                    "error": (
                        f"Discovery failed for "
                        f"city '{city_clean}'"
                    ),
                    "source": "overpass",
                    "error_type": "no_fallback",
                }
            ]

        lat, lon, radius = center

        try:

            query = self._build_around_query(
                lat,
                lon,
                radius,
                business_type_clean,
                limit,
            )

            data = await self._post_overpass_async(
                query
            )

            return self._parse_elements(
                data,
                business_type_clean,
                limit,
            )

        except Exception as exc:

            logger.exception(
                "Async Overpass around failed "
                "city=%s type=%s",
                city_clean,
                business_type_clean,
            )

            return [
                {
                    "error": str(exc),
                    "source": "overpass",
                    "error_type": "provider_failure",
                    "city": city_clean,
                    "business_type": business_type_clean,
                }
            ]

    # ========================================================
    # GOOGLE PLACES
    # ========================================================

    async def enrich_with_places(
        self,
        businesses: List[Dict],
        api_key: str,
    ) -> List[Dict]:
        """
        Optional Google Places enrichment.

        Requires:
        - GOOGLE_PLACES_ENABLED=True
        - Organization/user API key
        """

        if not settings.GOOGLE_PLACES_ENABLED:
            return businesses

        if not api_key:
            logger.warning(
                "Google Places enabled but no API key provided"
            )
            return businesses

        # Stage 1 intentionally remains cost-isolated.
        # Implement Places enrichment separately.
        return businesses