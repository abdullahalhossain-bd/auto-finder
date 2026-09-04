"""
Natural Language → Structured Campaign Parameters

Stage 1: Simple rule + keyword based parser.
Later can be upgraded with LLM for more complex parsing.
"""
from typing import Dict, Any, Optional
import re


class NLParserService:
    """Parse natural language campaign descriptions into structured params."""

    COUNTRY_HINTS = {
        "poland": "Poland", "polska": "Poland",
        "germany": "Germany", "deutschland": "Germany",
        "uk": "United Kingdom", "england": "United Kingdom", "britain": "United Kingdom",
        "usa": "United States", "us": "United States", "america": "United States",
        "india": "India", "bangladesh": "Bangladesh",
        "canada": "Canada", "australia": "Australia",
    }

    BUSINESS_HINTS = {
        "barber": "barber", "barbershop": "barber", "hairdresser": "hairdresser",
        "salon": "hairdresser", "restaurant": "restaurant", "cafe": "cafe",
        "coffee": "cafe", "dentist": "dentist", "doctor": "doctor", "clinic": "doctor",
        "plumber": "plumber", "electrician": "electrician", "gym": "gym",
        "fitness": "gym", "hotel": "hotel", "shop": "shop", "store": "shop",
    }

    SERVICE_HINTS = {
        "website": "website", "web site": "website", "web design": "website",
        "booking": "booking_system", "online booking": "booking_system",
        "reservation": "booking_system", "seo": "seo",
    }

    # Well-known cities → country. Used ONLY to fill in `country` when the
    # user names a recognizable city but never states a country explicitly
    # (e.g. "restaurants in Chicago"). This is a lookup of real-world facts,
    # not a guess — we never fabricate `city` or `business_type` this way,
    # and if the city isn't in this table we simply leave country unset.
    CITY_COUNTRY_HINTS = {
        "new york city": "United States", "new york": "United States", "nyc": "United States",
        "los angeles": "United States", "chicago": "United States", "san francisco": "United States",
        "houston": "United States", "miami": "United States", "boston": "United States",
        "seattle": "United States", "austin": "United States", "dallas": "United States",
        "philadelphia": "United States", "san diego": "United States", "denver": "United States",
        "krakow": "Poland", "cracow": "Poland", "warsaw": "Poland", "gdansk": "Poland",
        "wroclaw": "Poland", "poznan": "Poland",
        "berlin": "Germany", "munich": "Germany", "hamburg": "Germany", "frankfurt": "Germany",
        "cologne": "Germany",
        "london": "United Kingdom", "manchester": "United Kingdom", "birmingham": "United Kingdom",
        "leeds": "United Kingdom", "glasgow": "United Kingdom",
        "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada", "calgary": "Canada",
        "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia", "perth": "Australia",
        "mumbai": "India", "delhi": "India", "bangalore": "India", "new delhi": "India",
        "dhaka": "Bangladesh", "chittagong": "Bangladesh", "sylhet": "Bangladesh",
    }

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Extract structured parameters from natural language.
        Returns a dict ready to store in campaign.structured_params.
        Fields that genuinely cannot be determined stay None — callers must
        not fabricate them; the API layer is responsible for surfacing a
        validation error to the user instead of silently proceeding.
        """
        lower = text.lower()

        country = None
        for key, val in self.COUNTRY_HINTS.items():
            if key in lower:
                country = val
                break

        city = self._extract_city(text)

        if not country and city:
            country = self.CITY_COUNTRY_HINTS.get(city.lower())

        business_type = None
        for key, val in self.BUSINESS_HINTS.items():
            if key in lower:
                business_type = val
                break

        service = None
        for key, val in self.SERVICE_HINTS.items():
            if key in lower:
                service = val
                break

        min_reviews = None
        review_match = re.search(r"(\d+)\+?\s*reviews?", lower)
        if review_match:
            min_reviews = int(review_match.group(1))

        # "no/without/don't-doesn't-do not have (a) website (or ... booking system)"
        # covers phrasing like "do not have a website or online booking system",
        # where the negation applies to both nouns joined by "or"/"and".
        no_website_no_booking_shared = bool(
            re.search(
                r"(?:no|without|don't have|doesn't have|do not have|does not have)\s+"
                r"(?:a\s+|an\s+)?website\s+(?:or|and)\s+(?:an?\s+)?(?:online\s+)?booking",
                lower,
            )
        )
        no_website = no_website_no_booking_shared or any(
            x in lower
            for x in [
                "no website", "without website", "missing website",
                "don't have a website", "doesn't have a website",
                "do not have a website", "does not have a website",
            ]
        )
        no_booking = no_website_no_booking_shared or any(
            x in lower
            for x in [
                "no booking", "without booking", "no online booking",
                "don't have booking", "doesn't have booking",
                "don't have a booking", "doesn't have a booking",
                "do not have booking", "do not have a booking",
                "does not have booking", "does not have a booking",
            ]
        )

        return {
            "country": country,
            "city": city,
            "business_type": business_type,
            "service_offered": service or "website",
            "min_reviews": min_reviews or 0,
            "filters": {
                "no_website": no_website,
                "no_booking": no_booking,
            },
            "raw_input": text,
            "parser_version": "rule_v1",
        }

    def _extract_city(self, text: str) -> Optional[str]:
        # Primary: "in Krakow", "in New York", "at Warsaw", "near Chicago" — proper-noun style.
        match = re.search(
            r"\b(?:in|at|near)\s+([A-Z][a-zA-Z\s\-]+?)(?:\s+with|\s+that|\s+who|\s+and\b|\s*$|,|\.)",
            text,
        )
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate

        # Secondary: same prepositions but the city wasn't capitalized
        # ("in chicago", "near new york city").
        match = re.search(
            r"\b(?:in|at|near)\s+([a-zA-Z][a-zA-Z\s\-]+?)(?:\s+with|\s+that|\s+who|\s+and\b|\s*$|,|\.)",
            text,
        )
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() in self.CITY_COUNTRY_HINTS:
                return candidate.title()

        # Fallback: scan for a known city name anywhere in the text (handles
        # odd phrasing the prepositional patterns above miss). Longest names
        # first so "new york city" wins over "new york".
        lower = text.lower()
        for name in sorted(self.CITY_COUNTRY_HINTS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(name)}\b", lower):
                return name.title()

        return None