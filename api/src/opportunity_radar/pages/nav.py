"""The sidebar, one definition, read by base.html."""

from dataclasses import dataclass

from starlette.requests import Request


@dataclass(frozen=True)
class NavItem:
    label: str
    path: str
    icon: str
    group: str
    active: bool = False


_ITEMS = (
    ("Radar", "/", "mdi-radar", "Opportunities"),
    ("Consulting", "/opportunity?bucket=consulting", "mdi-briefcase-outline", "Opportunities"),
    ("Immediate", "/opportunity?bucket=immediate", "mdi-fire", "Opportunities"),
    ("Emerging", "/opportunity?bucket=emerging", "mdi-weather-partly-cloudy", "Opportunities"),
    ("Region gaps", "/region", "mdi-map-marker-radius-outline", "Opportunities"),
    ("Companies", "/company", "mdi-domain", "Evidence"),
    ("Signals", "/signal", "mdi-pulse", "Evidence"),
    ("Sources", "/source", "mdi-database-outline", "Evidence"),
    ("Profile", "/profile", "mdi-account-outline", "Me"),
)


def nav_items(request: Request) -> list[NavItem]:
    path = request.url.path
    query = request.url.query
    current = f"{path}?{query}" if query else path
    return [
        NavItem(
            label,
            item_path,
            icon,
            group,
            current == item_path or (item_path == path and "?" not in item_path),
        )
        for label, item_path, icon, group in _ITEMS
    ]
