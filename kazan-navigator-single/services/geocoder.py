"""
Сервис геокодирования: поиск мест и реверс-геокодинг.
Сначала локальная SQLite FTS5, потом Nominatim как fallback.
"""
import sqlite3
import requests

from config import (LOCAL_SEARCH_DB, NOMINATIM_URL, NOMINATIM_HEADERS,
                    KAZAN_CENTER, KAZAN_BBOX, KAZAN_RADIUS_M)
from extensions import cache
from utils import haversine, icon_for_category, extract_address


def get_local_db():
    """Подключение к локальной SQLite базе."""
    if not LOCAL_SEARCH_DB.exists():
        return None
    conn = sqlite3.connect(str(LOCAL_SEARCH_DB))
    conn.row_factory = sqlite3.Row
    return conn


def local_search(query, limit=20):
    """
    Локальный полнотекстовый поиск по SQLite FTS5.
    Возвращает список мест без обращения к интернету.
    """
    if not query or len(query) < 2:
        return []
    conn = get_local_db()
    if not conn:
        return []
    try:
        # FTS5 полнотекстовый поиск
        safe_q = query.replace('"', '""')
        rows = conn.execute(
            """SELECT p.id, p.name, p.address, p.category, p.icon, p.lat, p.lon
               FROM places_fts f
               JOIN places p ON p.id = f.rowid
               WHERE places_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (f'"{safe_q}"*', limit)
        ).fetchall()

        # Fallback на LIKE если FTS ничего не нашёл
        if not rows:
            rows = conn.execute(
                """SELECT id, name, address, category, icon, lat, lon
                   FROM places
                   WHERE name LIKE ? OR address LIKE ?
                   ORDER BY
                     CASE WHEN name LIKE ? THEN 0 ELSE 1 END,
                     length(name)
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"{query}%", limit)
            ).fetchall()

        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Local search error: {e}")
        return []
    finally:
        conn.close()


def nominatim_search(query, limit=8):
    """Онлайн-поиск через Nominatim (fallback)."""
    if not query or len(query) < 2:
        return []
    cache_key = f"search:{query.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    search_q = query if "казан" in query.lower() else f"{query}, Казань"
    try:
        r = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "format": "jsonv2", "q": search_q, "limit": limit,
                "addressdetails": 1, "accept-language": "ru",
                "countrycodes": "ru",
                "viewbox": KAZAN_BBOX, "bounded": 1,
            },
            headers=NOMINATIM_HEADERS, timeout=8,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    results = []
    for item in data:
        lat, lon = float(item["lat"]), float(item["lon"])
        if haversine(KAZAN_CENTER[0], KAZAN_CENTER[1], lat, lon) > KAZAN_RADIUS_M:
            continue
        name = item.get("name") or item.get("display_name", "").split(",")[0]
        results.append({
            "id": item.get("place_id"),
            "name": name,
            "display_name": item.get("display_name", ""),
            "lat": lat, "lon": lon,
            "type": item.get("type") or item.get("class"),
            "category": item.get("category") or item.get("class"),
            "icon": icon_for_category(item.get("class"), item.get("type")),
            "address": extract_address(item.get("address", {})),
        })
    cache.set(cache_key, results)
    return results


def reverse_geocode(lat, lon):
    """Реверс-геокодинг: координаты → адрес."""
    cache_key = f"rev:{float(lat):.5f}:{float(lon):.5f}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        r = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lon,
                    "addressdetails": 1, "accept-language": "ru"},
            headers=NOMINATIM_HEADERS, timeout=8,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"error": str(e)}

    result = {
        "display_name": data.get("display_name", ""),
        "address": extract_address(data.get("address", {})),
        "lat": float(data.get("lat", lat)),
        "lon": float(data.get("lon", lon)),
        "name": data.get("name") or data.get("display_name", "").split(",")[0],
        "type": data.get("type"),
    }
    cache.set(cache_key, result)
    return result


def search(query, limit=20):
    """
    Комбинированный поиск: сначала локальная БД, потом Nominatim.
    Возвращает объединённые результаты без дубликатов.
    """
    results = local_search(query, limit=limit)
    if len(results) < 3:
        online = nominatim_search(query, limit=limit)
        # Добавляем только уникальные
        seen = {r["name"].lower() for r in results}
        for r in online:
            if r["name"].lower() not in seen:
                results.append(r)
                seen.add(r["name"].lower())
    return results[:limit]


def find_nearby(lat, lon, radius=1500, limit=30, category=None):
    """Ближайшие места из локальной БД."""
    conn = get_local_db()
    if not conn:
        return []
    delta = radius / 111000
    try:
        if category:
            rows = conn.execute(
                """SELECT * FROM places
                   WHERE category = ? AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
                   LIMIT 200""",
                (category, lat - delta, lat + delta, lon - delta, lon + delta)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM places
                   WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
                   LIMIT 500""",
                (lat - delta, lat + delta, lon - delta, lon + delta)
            ).fetchall()

        items = []
        for r in rows:
            d = haversine(lat, lon, r["lat"], r["lon"])
            if d <= radius:
                item = dict(r)
                item["distance"] = int(d)
                from utils import format_distance
                item["distance_text"] = format_distance(d)
                items.append(item)
        items.sort(key=lambda x: x["distance"])
        return items[:limit]
    finally:
        conn.close()
