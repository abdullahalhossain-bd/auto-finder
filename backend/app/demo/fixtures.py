"""
Centralized realistic DEMO data (Bangladesh-focused).
No external APIs — static fixtures only. Labeled as Demo Data in product UI.
"""
from __future__ import annotations

from typing import Any

# Simulated source labels (never claim live query)
DEMO_SOURCES = ("google_maps", "google_search", "facebook", "osm")

DEMO_BUSINESSES: list[dict[str, Any]] = [
    {
        "name": "Sultans Dine Banani",
        "category": "Restaurant",
        "city": "Dhaka",
        "area": "Banani",
        "address": "Road 11, Banani, Dhaka 1213",
        "phone": "+8801711-234501",
        "email": "banani@sultansdine.example.bd",
        "website_url": None,
        "rating": 4.4,
        "review_count": 1280,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Kacchi Bhai Dhanmondi",
        "category": "Restaurant",
        "city": "Dhaka",
        "area": "Dhanmondi",
        "address": "Road 27, Dhanmondi, Dhaka 1209",
        "phone": "+8801812-445566",
        "email": None,
        "website_url": "http://kacchibhai-old.example.bd",
        "rating": 4.2,
        "review_count": 890,
        "source": "google_search",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Chillox Burger Gulshan",
        "category": "Restaurant",
        "city": "Dhaka",
        "area": "Gulshan",
        "address": "Gulshan Avenue, Dhaka 1212",
        "phone": "+8801911-778899",
        "email": "gulshan@chillox.example.bd",
        "website_url": "https://chillox.example.bd",
        "rating": 4.6,
        "review_count": 2100,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": False,
    },
    {
        "name": "Takeout Baily Road",
        "category": "Restaurant",
        "city": "Dhaka",
        "area": "Baily Road",
        "address": "New Baily Road, Dhaka 1000",
        "phone": "+8801612-334455",
        "email": None,
        "website_url": None,
        "rating": 4.3,
        "review_count": 640,
        "source": "facebook",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Mezban Chittagong Heritage",
        "category": "Restaurant",
        "city": "Chattogram",
        "area": "Agrabad",
        "address": "Agrabad C/A, Chattogram 4100",
        "phone": "+8801813-556677",
        "email": "info@mezban-ctg.example.bd",
        "website_url": None,
        "rating": 4.5,
        "review_count": 420,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Handi Crafts Banani Salon",
        "category": "Salon / Beauty",
        "city": "Dhaka",
        "area": "Banani",
        "address": "Block D, Banani, Dhaka 1213",
        "phone": "+8801715-998877",
        "email": "book@handicrafts-salon.example.bd",
        "website_url": "http://handicrafts-salon.example.bd",
        "rating": 4.7,
        "review_count": 310,
        "source": "google_search",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Glow Up Studio Uttara",
        "category": "Salon / Beauty",
        "city": "Dhaka",
        "area": "Uttara",
        "address": "Sector 7, Uttara, Dhaka 1230",
        "phone": "+8801914-223344",
        "email": None,
        "website_url": None,
        "rating": 4.1,
        "review_count": 95,
        "source": "facebook",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Fitness Zone Dhanmondi",
        "category": "Gym / Fitness",
        "city": "Dhaka",
        "area": "Dhanmondi",
        "address": "Road 8, Dhanmondi, Dhaka 1205",
        "phone": "+8801718-667788",
        "email": "membership@fitnesszone-dhn.example.bd",
        "website_url": "https://fitnesszone-dhn.example.bd",
        "rating": 4.4,
        "review_count": 520,
        "source": "google_maps",
        "has_booking": True,
        "website_weak": False,
    },
    {
        "name": "Pulse Gym Mirpur",
        "category": "Gym / Fitness",
        "city": "Dhaka",
        "area": "Mirpur",
        "address": "Mirpur 10, Dhaka 1216",
        "phone": "+8801819-112233",
        "email": None,
        "website_url": None,
        "rating": 4.0,
        "review_count": 180,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Green Leaf Dental Banani",
        "category": "Clinic / Healthcare",
        "city": "Dhaka",
        "area": "Banani",
        "address": "Road 12, Banani, Dhaka 1213",
        "phone": "+8802-9887766",
        "email": "appointments@greenleafdental.example.bd",
        "website_url": "http://greenleafdental.example.bd",
        "rating": 4.8,
        "review_count": 260,
        "source": "google_search",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "City Care Pharmacy Mohammadpur",
        "category": "Retail store",
        "city": "Dhaka",
        "area": "Mohammadpur",
        "address": "Town Hall, Mohammadpur, Dhaka 1207",
        "phone": "+8801712-445577",
        "email": None,
        "website_url": None,
        "rating": 4.2,
        "review_count": 74,
        "source": "osm",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Rangpur Kitchen Sylhet",
        "category": "Restaurant",
        "city": "Sylhet",
        "area": "Zindabazar",
        "address": "Zindabazar, Sylhet 3100",
        "phone": "+8801716-889900",
        "email": "orders@rangpurkitchen-syl.example.bd",
        "website_url": None,
        "rating": 4.3,
        "review_count": 155,
        "source": "facebook",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Cafe Mocha Bashundhara",
        "category": "Cafe",
        "city": "Dhaka",
        "area": "Bashundhara",
        "address": "Block C, Bashundhara R/A, Dhaka 1229",
        "phone": "+8801915-334466",
        "email": "mocha.bsh@example.bd",
        "website_url": "https://cafemocha-bsh.example.bd",
        "rating": 4.5,
        "review_count": 410,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": False,
    },
    {
        "name": "Woodland Furniture Tejgaon",
        "category": "Retail store",
        "city": "Dhaka",
        "area": "Tejgaon",
        "address": "Industrial Area, Tejgaon, Dhaka 1208",
        "phone": "+8802-8877665",
        "email": "sales@woodlandfurn.example.bd",
        "website_url": None,
        "rating": 4.1,
        "review_count": 88,
        "source": "google_search",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Lakeview Hotel Cox's Bazar",
        "category": "Hotel",
        "city": "Cox's Bazar",
        "area": "Kolatoli",
        "address": "Kolatoli Road, Cox's Bazar 4700",
        "phone": "+8801814-556600",
        "email": "reservations@lakeview-cxb.example.bd",
        "website_url": "http://lakeview-cxb.example.bd",
        "rating": 3.9,
        "review_count": 340,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "AutoCare Workshop Uttara",
        "category": "Auto service",
        "city": "Dhaka",
        "area": "Uttara",
        "address": "Sector 11, Uttara, Dhaka 1230",
        "phone": "+8801719-223355",
        "email": None,
        "website_url": None,
        "rating": 4.0,
        "review_count": 120,
        "source": "facebook",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Skyline Properties Gulshan",
        "category": "Real estate",
        "city": "Dhaka",
        "area": "Gulshan",
        "address": "Gulshan 2, Dhaka 1212",
        "phone": "+8802-9881122",
        "email": "leads@skylineprops.example.bd",
        "website_url": "https://skylineprops.example.bd",
        "rating": 4.3,
        "review_count": 67,
        "source": "google_search",
        "has_booking": False,
        "website_weak": False,
    },
    {
        "name": "Nawab's Kitchen Old Dhaka",
        "category": "Restaurant",
        "city": "Dhaka",
        "area": "Chawkbazar",
        "address": "Chawkbazar, Old Dhaka 1100",
        "phone": "+8801713-778811",
        "email": None,
        "website_url": None,
        "rating": 4.6,
        "review_count": 980,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Petals Flower Shop Bailey",
        "category": "Retail store",
        "city": "Dhaka",
        "area": "Baily Road",
        "address": "Baily Road, Dhaka 1000",
        "phone": "+8801816-445566",
        "email": "orders@petalsbailey.example.bd",
        "website_url": None,
        "rating": 4.4,
        "review_count": 52,
        "source": "osm",
        "has_booking": False,
        "website_weak": True,
    },
    {
        "name": "Orthopedic Care Center Panthapath",
        "category": "Clinic / Healthcare",
        "city": "Dhaka",
        "area": "Panthapath",
        "address": "Panthapath, Dhaka 1205",
        "phone": "+8802-9145566",
        "email": "desk@orthocare-path.example.bd",
        "website_url": "http://orthocare-path.example.bd",
        "rating": 4.5,
        "review_count": 190,
        "source": "google_maps",
        "has_booking": False,
        "website_weak": True,
    },
]

# Extra pool for up to 40 leads
_EXTRA_NAMES = [
    ("Tasty Treats Mirpur", "Restaurant", "Mirpur"),
    ("Spice Route Uttara", "Restaurant", "Uttara"),
    ("Cafe Adda Dhanmondi", "Cafe", "Dhanmondi"),
    ("Blend & Brew Gulshan", "Cafe", "Gulshan"),
    ("Style Cut Barber Banani", "Salon / Beauty", "Banani"),
    ("Nail Art Lounge Bashundhara", "Salon / Beauty", "Bashundhara"),
    ("Iron Temple Gym Tejgaon", "Gym / Fitness", "Tejgaon"),
    ("Yoga Shala Lalmatia", "Gym / Fitness", "Lalmatia"),
    ("Smile Dental Wari", "Clinic / Healthcare", "Wari"),
    ("City Optics New Market", "Retail store", "New Market"),
    ("Heritage Inn Bandarban", "Hotel", "Bandarban"),
    ("MotorWorks Keraniganj", "Auto service", "Keraniganj"),
    ("Homestead Realty Motijheel", "Real estate", "Motijheel"),
    ("River View Kitchen Barisal", "Restaurant", "Barisal"),
    ("Hilltop Cafe Khagrachhari", "Cafe", "Khagrachhari"),
    ("QuickFix Motors Gazipur", "Auto service", "Gazipur"),
    ("Garden Inn Rajshahi", "Hotel", "Rajshahi"),
    ("MediPlus Clinic Comilla", "Clinic / Healthcare", "Comilla"),
    ("Book Nook Library Cafe", "Cafe", "Dhanmondi"),
    ("Biryani House Jatrabari", "Restaurant", "Jatrabari"),
]


def _expand_pool() -> list[dict[str, Any]]:
    out = list(DEMO_BUSINESSES)
    phones = 1700000000
    sources = list(DEMO_SOURCES)
    for i, (name, cat, area) in enumerate(_EXTRA_NAMES):
        phones += 17
        out.append(
            {
                "name": name,
                "category": cat,
                "city": "Dhaka" if area not in ("Barisal", "Khagrachhari", "Gazipur", "Rajshahi", "Comilla", "Bandarban") else area,
                "area": area,
                "address": f"{area}, Bangladesh",
                "phone": f"+8801{str(phones)[-9:]}",
                "email": None if i % 3 else f"contact@{name.lower().replace(' ', '')[:12]}.example.bd",
                "website_url": None if i % 2 else f"http://{name.lower().replace(' ', '')[:14]}.example.bd",
                "rating": round(3.8 + (i % 10) * 0.1, 1),
                "review_count": 40 + i * 23,
                "source": sources[i % len(sources)],
                "has_booking": i % 7 == 0,
                "website_weak": i % 2 == 1,
            }
        )
    return out


DEMO_POOL = _expand_pool()


def filter_demo_businesses(
    *,
    industry: str | None = None,
    city: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    items = DEMO_POOL
    if city:
        c = city.lower().strip()
        filtered = [b for b in items if c in (b.get("city") or "").lower() or c in (b.get("area") or "").lower()]
        if filtered:
            items = filtered
    if industry and industry.lower() not in ("other local business", "other"):
        ind = industry.lower().split("/")[0].strip()
        filtered = [b for b in items if ind in (b.get("category") or "").lower()]
        if filtered:
            items = filtered
    # Deterministic "score"
    scored = []
    for b in items:
        score = 20.0
        if not b.get("website_url"):
            score += 40
        elif b.get("website_weak"):
            score += 25
        if b.get("review_count", 0) >= 50 and not b.get("has_booking"):
            score += 35
        elif b.get("review_count", 0) >= 20 and not b.get("has_booking"):
            score += 20
        if b.get("phone"):
            score += 5
        score = min(100.0, score)
        row = dict(b)
        row["opportunity_score"] = score
        if score >= 80:
            row["tier"] = "hot"
            row["tier_label"] = "Strong fit"
        elif score >= 65:
            row["tier"] = "qualified"
            row["tier_label"] = "Good fit"
        elif score >= 45:
            row["tier"] = "medium"
            row["tier_label"] = "Medium"
        else:
            row["tier"] = "low"
            row["tier_label"] = "Weak"
        scored.append(row)
    scored.sort(key=lambda x: -x["opportunity_score"])
    return scored[: max(1, min(limit, 40))]


DEMO_ACCOUNTS = {
    "demo.user": {
        "email": "demo.user@localopp.demo",
        "password": "DemoUser123!",
        "org_name": "Horizon Web Studio",
        "plan": "trial",
        "role": "owner",
        "is_platform_admin": False,
        "label": "Free user",
    },
    "demo.pro": {
        "email": "demo.pro@localopp.demo",
        "password": "DemoPro123!",
        "org_name": "Delta Digital Agency",
        "plan": "pro",
        "role": "owner",
        "is_platform_admin": False,
        "label": "Pro user",
    },
    "demo.admin": {
        "email": "demo.admin@localopp.demo",
        "password": "DemoAdmin123!",
        "org_name": "LocalOpp Platform",
        "plan": "pro",
        "role": "owner",
        "is_platform_admin": True,
        "label": "Platform admin",
    },
}


def demo_message_for_lead(business: dict[str, Any], service: str = "websites and online booking") -> dict[str, str]:
    name = business.get("name") or "there"
    city = business.get("city") or "your area"
    gap = "website" if not business.get("website_url") else "online booking"
    subject = f"Quick idea for {name}"
    body = (
        f"Hi {name} team,\n\n"
        f"I was looking at local {business.get('category', 'businesses').lower()} in {city} and noticed "
        f"{name} has strong reviews"
        + (f" ({business.get('review_count')} on listing sites)" if business.get("review_count") else "")
        + f" but still seems to rely on walk-ins more than a clear {gap}.\n\n"
        f"We help similar businesses in Bangladesh set up {service} so customers can find you and book faster. "
        f"Would you be open to a 10-minute call this week?\n\n"
        f"Best regards\n"
    )
    rationale = (
        f"[Demo Mode] Deterministic draft from mock lead fields "
        f"(name, city, reviews, missing {gap}). No external AI API was called."
    )
    return {"subject": subject, "body": body, "rationale": rationale}


def demo_customer_reply(intent: str = "positive") -> dict[str, Any]:
    if intent == "positive":
        return {
            "text": "Thanks for reaching out. We have been thinking about online booking for the Banani branch. Can you share pricing and a sample site?",
            "intent": "positive",
            "intent_confidence": 0.87,
            "intent_label": "Positive Intent — 87%",
            "suggested_reply": (
                "Glad to hear that — I can send two sample pages and a simple package for a single-location booking site. "
                "Are you free Thursday after 4pm Bangladesh time?"
            ),
        }
    if intent == "later":
        return {
            "text": "Not this month — maybe after Ramadan. Please follow up in June.",
            "intent": "later",
            "intent_confidence": 0.81,
            "intent_label": "Follow up later — 81%",
            "suggested_reply": "Understood — I will check back in early June. Wishing you a busy season until then.",
        }
    return {
        "text": "Please remove us from your list.",
        "intent": "unsubscribe",
        "intent_confidence": 0.94,
        "intent_label": "Do not contact — 94%",
        "suggested_reply": "You are removed from outreach. Sorry for the interruption.",
    }
