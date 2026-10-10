"""Resolves a posting's free-text location to ISO country codes. Keyword table, no geocoder, no network.

Only the location and remote_detail fields are read, never the description, so a passing "join us" cannot
become a US match. A string that names no known place resolves to nothing; regions ("Europe", "EMEA") are
deliberately not countries and resolve to nothing too.
"""

import re

from loguru import logger

from opportunity_radar.db import execute, rows, transaction

# code -> place words found in location strings (lowercase). Ambiguous names (Cambridge, Georgia, Victoria)
# are left out on purpose; a wrong country is worse than no country.
_PLACES: dict[str, tuple[str, ...]] = {
    "US": (
        "united states",
        "usa",
        "us",
        "u.s.",
        "us-remote",
        "new york",
        "nyc",
        "san francisco",
        "sf",
        "seattle",
        "austin",
        "chicago",
        "boston",
        "los angeles",
        "denver",
        "atlanta",
        "miami",
        "washington, dc",
        "washington dc",
        "palo alto",
        "mountain view",
        "menlo park",
        "san jose",
        "oakland",
        "portland",
        "salt lake city",
        "dallas",
        "houston",
        "phoenix",
        "philadelphia",
        "pittsburgh",
        "raleigh",
        "durham",
        "nashville",
        "minneapolis",
        "detroit",
        "omaha",
        "san diego",
        "sunnyvale",
        "redwood city",
        "santa clara",
        "bellevue",
        "brooklyn",
        "california",
        "texas",
        "colorado",
        "massachusetts",
        "virginia",
    ),
    "CA": ("canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "waterloo"),
    "MX": ("mexico", "méxico", "mexico city", "guadalajara", "monterrey"),
    "BR": ("brazil", "brasil", "são paulo", "sao paulo", "rio de janeiro", "florianópolis"),
    "AR": ("argentina", "buenos aires"),
    "CO": ("colombia", "bogotá", "bogota", "medellín", "medellin"),
    "CL": ("chile", "santiago"),
    "GB": (
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "london",
        "manchester",
        "cardiff",
        "edinburgh",
        "bristol",
        "cambridge, uk",
        "oxford",
        "leeds",
        "birmingham",
        "glasgow",
        "belfast",
    ),
    "IE": ("ireland", "dublin", "cork", "galway"),
    "DE": (
        "germany",
        "deutschland",
        "berlin",
        "munich",
        "münchen",
        "hamburg",
        "frankfurt",
        "cologne",
        "köln",
        "düsseldorf",
        "dusseldorf",
        "stuttgart",
        "leipzig",
        "dresden",
        "nuremberg",
        "nürnberg",
        "hannover",
        "karlsruhe",
        "heidelberg",
        "bexbach",
        "chemnitz",
        "sachsen",
        "bayern",
        "brandenburg",
        "hessen",
        "nordrhein-westfalen",
        "baden-württemberg",
        "bonn",
        "mannheim",
        "essen",
        "dortmund",
        "bremen",
        "münster",
        "aachen",
        "mainz",
        "wiesbaden",
        "darmstadt",
        "potsdam",
        "ingolstadt",
        "regensburg",
        "augsburg",
        "freiburg",
        "walldorf",
    ),
    "FR": (
        "france",
        "paris",
        "lyon",
        "marseille",
        "toulouse",
        "nantes",
        "bordeaux",
        "lille",
        "arrondissement",
        "saint-denis",
        "niort",
        "rennes",
        "strasbourg",
        "grenoble",
        "montpellier",
        "nice",
        "île-de-france",
        "ile-de-france",
        "sophia antipolis",
    ),
    "NL": ("netherlands", "the netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague"),
    "BE": ("belgium", "brussels", "bruxelles", "antwerp", "ghent", "gent", "leuven"),
    "CH": (
        "switzerland",
        "schweiz",
        "suisse",
        "zurich",
        "zürich",
        "geneva",
        "genf",
        "genève",
        "bern",
        "basel",
        "lausanne",
        "liebefeld",
        "zug",
        "steinhausen",
        "lugano",
        "winterthur",
        "luzern",
        "lucerne",
        "st. gallen",
    ),
    "AT": ("austria", "österreich", "vienna", "wien", "graz", "linz"),
    "ES": (
        "spain",
        "españa",
        "madrid",
        "barcelona",
        "valencia",
        "sevilla",
        "seville",
        "málaga",
        "malaga",
        "bilbao",
    ),
    "PT": ("portugal", "lisbon", "lisboa", "porto", "braga"),
    "IT": ("italy", "italia", "milan", "milano", "rome", "roma", "turin", "torino", "bologna", "florence"),
    "PL": (
        "poland",
        "polska",
        "warsaw",
        "warszawa",
        "krakow",
        "kraków",
        "wroclaw",
        "wrocław",
        "gdansk",
        "gdańsk",
        "poznan",
    ),
    "CZ": ("czech", "czechia", "prague", "praha", "brno"),
    "HU": ("hungary", "budapest"),
    "RO": ("romania", "bucharest", "cluj"),
    "BG": ("bulgaria", "sofia"),
    "GR": ("greece", "athens", "thessaloniki"),
    "HR": ("croatia", "zagreb"),
    "RS": ("serbia", "belgrade"),
    "UA": ("ukraine", "kyiv", "kiev", "lviv"),
    "SE": ("sweden", "stockholm", "gothenburg", "göteborg", "malmö", "malmo"),
    "DK": ("denmark", "copenhagen", "københavn", "aarhus"),
    "NO": ("norway", "oslo", "bergen"),
    "FI": ("finland", "helsinki", "espoo", "tampere"),
    "EE": ("estonia", "tallinn", "tartu"),
    "LV": ("latvia", "riga"),
    "LT": ("lithuania", "vilnius", "kaunas"),
    "TR": ("turkey", "türkiye", "istanbul", "ankara", "izmir"),
    "IL": ("israel", "tel aviv", "tel-aviv", "jerusalem", "haifa", "herzliya"),
    "AE": ("united arab emirates", "uae", "dubai", "abu dhabi"),
    "SA": ("saudi arabia", "saudi", "riyadh", "jeddah", "ksa"),
    "QA": ("qatar", "doha"),
    "BH": ("bahrain", "manama"),
    "KW": ("kuwait",),
    "OM": ("oman", "muscat"),
    "EG": ("egypt", "cairo"),
    "NG": ("nigeria", "lagos", "abuja"),
    "KE": ("kenya", "nairobi"),
    "ZA": ("south africa", "cape town", "johannesburg", "pretoria", "durban"),
    "IN": (
        "india",
        "bengaluru",
        "bangalore",
        "mumbai",
        "pune",
        "hyderabad",
        "chennai",
        "delhi",
        "new delhi",
        "gurgaon",
        "gurugram",
        "noida",
        "kolkata",
        "ahmedabad",
        "kochi",
        "jaipur",
        "chandigarh",
    ),
    "PK": ("pakistan", "karachi", "lahore", "islamabad"),
    "BD": ("bangladesh", "dhaka"),
    "LK": ("sri lanka", "colombo"),
    "SG": ("singapore",),
    "MY": ("malaysia", "kuala lumpur", "penang"),
    "ID": ("indonesia", "jakarta", "bandung"),
    "TH": ("thailand", "bangkok"),
    "VN": ("vietnam", "viet nam", "ho chi minh", "hanoi", "da nang"),
    "PH": ("philippines", "manila", "cebu"),
    "HK": ("hong kong",),
    "TW": ("taiwan", "taipei", "hsinchu"),
    "CN": ("china", "beijing", "shanghai", "shenzhen", "hangzhou", "guangzhou"),
    "JP": ("japan", "tokyo", "osaka", "kyoto", "fukuoka", "nagoya", "yokohama"),
    "KR": ("south korea", "korea", "seoul", "busan", "pangyo", "seongnam"),
    "AU": ("australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra"),
    "NZ": ("new zealand", "auckland", "wellington", "christchurch"),
}
# US postal abbreviations only count after a comma: "San Francisco, CA" yes, "CA" alone (Canada?) no.
_US_STATES = (
    "al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh "
    "ok or pa ri sc sd tn tx ut vt va wa wv wi wy dc"
).split()
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (code, re.compile(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])"))
    for code, words in _PLACES.items()
    for word in words
]
_US_STATE_RE = re.compile(r",\s*(" + "|".join(_US_STATES) + r")(?![a-z])")


def countries_of(location: str | None, remote_detail: str | None = None) -> list[str]:
    text = f"{location or ''} {remote_detail or ''}".lower()
    if not text.strip():
        return []
    found = {code for code, pattern in _PATTERNS if pattern.search(text)}
    if _US_STATE_RE.search(text):
        found.add("US")
    return sorted(found)


def resolve_all() -> int:
    """Recomputes `countries` for every open posting and refreshes company.country from them. Returns changed rows."""
    changed = 0
    with transaction() as connection:
        postings = rows(
            connection,
            "SELECT id, location, remote_detail, countries FROM job_posting WHERE closed_at IS NULL",
        )
        for posting in postings:
            codes = countries_of(posting["location"], posting["remote_detail"])
            if codes != sorted(posting["countries"]):
                changed += execute(
                    connection,
                    "UPDATE job_posting SET countries = :c WHERE id = :id",
                    {"c": codes, "id": posting["id"]},
                )
        # company.country = the single most common country across its open postings; cleared when none resolves
        execute(
            connection,
            """WITH ranked AS (
                   SELECT company_id, code, count(*) AS n,
                          row_number() OVER (PARTITION BY company_id ORDER BY count(*) DESC, code) AS rank
                   FROM job_posting p, unnest(p.countries) AS code
                   WHERE p.closed_at IS NULL GROUP BY company_id, code)
               UPDATE company c SET country = r.code, updated_at = now()
               FROM ranked r WHERE r.company_id = c.id AND r.rank = 1 AND c.country IS DISTINCT FROM r.code""",
        )
    logger.info(f"geo: {changed} postings re-resolved out of {len(postings)} open")
    return changed
