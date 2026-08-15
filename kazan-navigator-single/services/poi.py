"""
Сервис POI: загрузка из OpenStreetMap через Overpass API.
"""
import requests
from config import OVERPASS_URL, KAZAN_OVERPASS_BBOX
from extensions import cache
from utils import icon_for_category


_POI_FILTERS = {
    "food": 'node["amenity"~"restaurant|cafe|fast_food|bar|pub"]',
    "fuel": 'node["amenity"="fuel"]',
    "pharmacy": 'node["amenity"="pharmacy"]',
    "hospital": 'node["amenity"~"hospital|clinic"]',
    "bank": 'node["amenity"~"bank|atm"]',
    "shop": 'node["shop"]',
    "supermarket": 'node["shop"~"supermarket|convenience"]',
    "parking": 'node["amenity"="parking"]',
}


def get_pois(category):
    """POI по категории из OSM."""
    if category not in _POI_FILTERS:
        return {"error": f"Неизвестная категория: {category}"}

    cache_key = f"pois:{category}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    query = f'[out:json][timeout:25];({_POI_FILTERS[category]}({KAZAN_OVERPASS_BBOX}););out center 80;'
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=30,
                          headers={"User-Agent": "KazanNavigator/3.1"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": f"Overpass недоступен: {e}"}

    items = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if not lat or not lon:
            continue
        name = tags.get("name") or tags.get("brand") or "Без названия"
        items.append({
            "id": el.get("id"), "name": name, "lat": lat, "lon": lon,
            "category": category,
            "icon": icon_for_category(tags.get("amenity") and "amenity",
                                      tags.get("amenity") or tags.get("shop")),
            "tags": {"phone": tags.get("phone"), "website": tags.get("website"),
                     "opening_hours": tags.get("opening_hours"),
                     "brand": tags.get("brand")},
        })

    response = {"category": category, "count": len(items), "items": items}
    cache.set(cache_key, response)
    return response
