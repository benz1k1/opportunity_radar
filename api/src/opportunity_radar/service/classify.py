"""Pure text classification for postings: family, seniority, tech, remote scope, rate, language."""

import html
import re
from dataclasses import dataclass
from decimal import Decimal

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

FAMILIES: dict[str, tuple[str, ...]] = {
    "ml": (
        "machine learning",
        "ml engineer",
        "ai engineer",
        "llm",
        "data scientist",
        "nlp",
        "computer vision",
        "research scientist",
        "applied scientist",
        "deep learning",
    ),
    "data": (
        "data engineer",
        "analytics engineer",
        "etl",
        "data platform",
        "warehouse",
        "dbt",
        "data infrastructure",
        "bi engineer",
    ),
    "devops": (
        "devops",
        "sre",
        "site reliability",
        "infrastructure engineer",
        "platform engineer",
        "cloud engineer",
        "kubernetes",
    ),
    "mobile": ("ios", "android", "mobile", "flutter", "react native"),
    "frontend": (
        "frontend",
        "front-end",
        "front end",
        "react",
        "angular",
        "vue",
        "ui engineer",
        "web developer",
    ),
    "qa": ("qa ", "quality", "test engineer", "sdet", "tester"),
    "security": ("security", "appsec", "infosec"),
    "backend": (
        "backend",
        "back-end",
        "back end",
        "java",
        "python",
        "golang",
        "node",
        "api",
        "software engineer",
        "software developer",
        "ruby",
        ".net",
        "php",
        "scala",
        "rust",
        "fullstack",
        "full stack",
        "full-stack",
        "engineer",
    ),
}
ENGINEERING_FAMILIES = frozenset({"backend", "frontend", "data", "devops", "ml", "mobile", "qa", "security"})

# canonical name -> patterns found in text
TECH: dict[str, tuple[str, ...]] = {
    "java": (r"\bjava\b",),
    "kotlin": (r"\bkotlin\b",),
    "spring": (r"\bspring\b",),
    "scala": (r"\bscala\b",),
    "python": (r"\bpython\b",),
    "django": (r"\bdjango\b",),
    "fastapi": (r"\bfastapi\b",),
    "flask": (r"\bflask\b",),
    "go": (r"\bgolang\b", r"\bgo\b(?= developer| engineer|,|/)"),
    "node": (r"\bnode(\.js)?\b",),
    "typescript": (r"\btypescript\b",),
    "react": (r"\breact(\.js)?\b",),
    "angular": (r"\bangular\b",),
    "vue": (r"\bvue(\.js)?\b",),
    "postgresql": (r"\bpostgres(ql)?\b",),
    "mysql": (r"\bmysql\b",),
    "sql": (r"\bsql\b",),
    "mongodb": (r"\bmongo(db)?\b",),
    "kafka": (r"\bkafka\b",),
    "redis": (r"\bredis\b",),
    "elasticsearch": (r"\belasticsearch\b",),
    "graphql": (r"\bgraphql\b",),
    "aws": (r"\baws\b",),
    "gcp": (r"\bgcp\b", r"google cloud"),
    "azure": (r"\bazure\b",),
    "kubernetes": (r"\bkubernetes\b", r"\bk8s\b"),
    "docker": (r"\bdocker\b",),
    "terraform": (r"\bterraform\b",),
    "airflow": (r"\bairflow\b",),
    "spark": (r"\bspark\b",),
    "snowflake": (r"\bsnowflake\b",),
    "dbt": (r"\bdbt\b",),
    "etl": (r"\betl\b", r"data pipelines?"),
    "microservices": (r"\bmicroservices?\b",),
    "llm": (r"\bllms?\b", r"large language model"),
    "openai": (r"\bopenai\b", r"\bgpt-?\d"),
    "anthropic": (r"\banthropic\b", r"\bclaude\b"),
    "rag": (r"\brag\b", r"retrieval[- ]augmented"),
    "langchain": (r"\blangchain\b",),
    "pytorch": (r"\bpytorch\b",),
    "tensorflow": (r"\btensorflow\b",),
    "wordpress": (r"\bwordpress\b",),
    "woocommerce": (r"\bwoocommerce\b",),
    "shopify": (r"\bshopify\b",),
    "php": (r"\bphp\b",),
    "ruby": (r"\bruby\b", r"\brails\b"),
    ".net": (r"\.net\b", r"\bc#"),
    "rust": (r"\brust\b",),
}
_TECH_RE = {
    name: [re.compile(pattern, re.IGNORECASE) for pattern in patterns] for name, patterns in TECH.items()
}
AI_TECH = frozenset({"llm", "openai", "anthropic", "rag", "langchain"})
OLD_STACK = frozenset({"wordpress", "woocommerce", "php"})

_NON_ENGLISH_MARKERS = re.compile(
    r"\((m/w/d|w/m/d|m/f/d|f/m/d|m/w/x|all genders)\)|\b(und|für|mit|der|die|das|wir|suchen|ingeniero|desarrollador|développeur|sviluppatore)\b",
    re.IGNORECASE,
)
_NON_ASCII_LETTER = re.compile(r"[^\x00-\x7F]")


def strip_html(text: str) -> str:
    return _WS.sub(" ", _TAG.sub(" ", html.unescape(text or ""))).strip()


def is_english(title: str, description: str) -> bool:
    sample = f"{title} {description[:1500]}"
    if _NON_ENGLISH_MARKERS.search(title) or len(_NON_ENGLISH_MARKERS.findall(sample)) >= 3:
        return False
    if not sample:
        return True
    return len(_NON_ASCII_LETTER.findall(sample)) / len(sample) < 0.05


def family_of(title: str) -> str:
    lowered = f" {title.lower()} "
    for family, keywords in FAMILIES.items():
        if any(keyword in lowered for keyword in keywords):
            return family
    return "other"


def seniority_of(title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ("intern", "junior", "graduate", "entry", "associate")):
        return "junior"
    if any(
        word in lowered
        for word in ("staff", "principal", "lead", "head of", "architect", "director", "distinguished")
    ):
        return "lead"
    if any(word in lowered for word in ("senior", "sr.", "sr ")):
        return "senior"
    return "mid"


def tech_of(text: str) -> list[str]:
    return sorted(
        name for name, patterns in _TECH_RE.items() if any(pattern.search(text) for pattern in patterns)
    )


def remote_scope_of(location: str, description: str, remote_hint: bool | None) -> tuple[str, str]:
    """Returns (scope, detail). Scope: worldwide | region | country | onsite | unknown."""
    where = (location or "").lower()
    head = description[:600].lower()
    text = f"{where} {head}"
    if remote_hint is False and "remote" not in where:
        return "onsite", location or ""
    if any(
        word in text for word in ("worldwide", "anywhere", "globally", "global remote", "work from anywhere")
    ):
        return "worldwide", location or "worldwide"
    if "remote" in text or remote_hint:
        for marker, scope in (
            ("emea", "region"),
            ("europe", "region"),
            ("apac", "region"),
            ("latam", "region"),
            ("americas", "region"),
            ("us only", "country"),
            ("united states", "country"),
            ("usa", "country"),
            ("canada", "country"),
            ("uk", "country"),
            ("united kingdom", "country"),
            ("germany", "country"),
            ("india", "country"),
            ("australia", "country"),
            ("japan", "country"),
            ("singapore", "country"),
        ):
            if marker in where:
                return scope, location
        return "unknown", location or "remote"
    if where:
        return "onsite", location
    return "unknown", ""


def employment_type_of(title: str, hint: str) -> str:
    text = f"{title} {hint}".lower()
    if any(word in text for word in ("contract", "freelance", "contractor", "consultant")):
        return "contract"
    if "part" in text and "time" in text:
        return "parttime"
    if any(word in text for word in ("full", "permanent")):
        return "fulltime"
    return "unknown"


@dataclass(frozen=True)
class Rate:
    minimum: Decimal | None
    maximum: Decimal | None
    currency: str
    period: str  # hour | month | year


_CURRENCY = {
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "₹": "INR",
    "inr": "INR",
    "¥": "JPY",
    "jpy": "JPY",
    "aed": "AED",
    "sgd": "SGD",
    "a$": "AUD",
    "aud": "AUD",
    "cad": "CAD",
    "c$": "CAD",
    "chf": "CHF",
}
_RATE = re.compile(
    r"(?P<cur>us\$|a\$|c\$|[$€£₹¥]|usd|eur|gbp|inr|jpy|aed|sgd|aud|cad|chf)\s?(?P<min>\d[\d,.]*)\s?(?P<k1>k)?"
    r"(?:\s?(?:-|–|to)\s?(?:us\$|a\$|c\$|[$€£₹¥])?\s?(?P<max>\d[\d,.]*)\s?(?P<k2>k)?)?"
    r"(?P<per>\s?(?:/|per)\s?(?:hour|hr|h|month|mo|year|yr|annum|a)\b)?",
    re.IGNORECASE,
)


def rate_of(text: str) -> Rate | None:
    found = _RATE.search(text or "")
    if not found:
        return None

    def number(raw: str | None, thousands: str | None) -> Decimal | None:
        if not raw:
            return None
        value = Decimal(raw.replace(",", "").rstrip("."))
        return value * 1000 if thousands else value

    minimum = number(found.group("min"), found.group("k1"))
    maximum = number(found.group("max"), found.group("k2")) or minimum
    per = (found.group("per") or "").lower()
    if any(unit in per for unit in ("hour", "hr", "/h", "per h")):
        period = "hour"
    elif any(unit in per for unit in ("month", "mo")):
        period = "month"
    elif per or (minimum is not None and minimum >= 10000):
        period = "year"
    elif minimum is not None and minimum < 500:
        period = "hour"
    else:
        period = "month"
    return Rate(minimum, maximum, _CURRENCY[found.group("cur").lower()], period)
