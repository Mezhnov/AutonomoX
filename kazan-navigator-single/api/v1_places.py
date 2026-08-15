"""
API v1: Места Казани (как 2GIS/Яндекс.Карты).
Поиск, детали, ближайшие, по категории.
"""
from flask import Blueprint, request, jsonify
from api.middleware import require_api_key
from services.geocoder import local_search, search, find_nearby
from api.attractions import ATTRACTIONS
from utils import haversine, format_distance

v1_places_bp = Blueprint("v1_places", __name__, url_prefix="/api/v1")


@v1_places_bp.route("/places")
@require_api_key
def v1_places():
    """
    Поиск мест в Казани.

    **Параметры:**
    - `q` (обяз.) — поисковый запрос (название, адрес)
    - `limit` (опц., макс. 50) — количество результатов
    - `category` (опц.) — фильтр по категории (cafe, restaurant, pharmacy, и т.д.)

    **Возвращает:** массив мест с координатами
    """
    q = (request.args.get("q") or "").strip()
    limit = min(request.args.get("limit", default=20, type=int), 50)
    category = request.args.get("category")

    if len(q) < 2:
        return jsonify({"error": "Минимум 2 символа", "code": "BAD_REQUEST"}), 400

    results = search(q, limit=limit)
    if category:
        results = [r for r in results if r.get("category", "").startswith(category)]

    return jsonify({
        "query": q,
        "count": len(results),
        "places": results,
    })


@v1_places_bp.route("/places/nearby")
@require_api_key
def v1_places_nearby():
    """
    Ближайшие места к точке.

    **Параметры:**
    - `lat` (обяз.) — широта
    - `lon` (обяз.) — долгота
    - `radius` (опц., по умолч. 1500) — радиус в метрах
    - `category` (опц.) — фильтр по категории
    - `limit` (опц., макс. 100) — количество результатов
    """
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", default=1500, type=int)
    limit = min(request.args.get("limit", default=30, type=int), 100)
    category = request.args.get("category")

    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны", "code": "BAD_REQUEST"}), 400

    items = find_nearby(lat, lon, radius, limit, category)
    return jsonify({
        "count": len(items),
        "places": items,
        "search_center": {"lat": lat, "lon": lon, "radius": radius},
    })


@v1_places_bp.route("/places/categories")
@require_api_key
def v1_places_categories():
    """Список всех категорий мест с количеством."""
    import sqlite3
    from config import LOCAL_SEARCH_DB
    if not LOCAL_SEARCH_DB.exists():
        return jsonify({"error": "База не построена"}), 503
    conn = sqlite3.connect(str(LOCAL_SEARCH_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM places GROUP BY category ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return jsonify({
        "count": len(rows),
        "categories": [dict(r) for r in rows],
    })


@v1_places_bp.route("/attractions")
@require_api_key
def v1_attractions():
    """
    Достопримечательности Казани.

    **Параметры:**
    - `category` (опц.) — история, религия, архитектура, музеи, парки
    """
    category = request.args.get("category")
    items = ATTRACTIONS
    if category and category != "all":
        items = [a for a in ATTRACTIONS if a["category"] == category]
    return jsonify({
        "count": len(items),
        "attractions": items,
    })


@v1_places_bp.route("/attractions/<attraction_id>")
@require_api_key
def v1_attraction_detail(attraction_id):
    """Детали достопримечательности."""
    for a in ATTRACTIONS:
        if a["id"] == attraction_id:
            return jsonify(a)
    return jsonify({"error": "Не найдено", "code": "NOT_FOUND"}), 404


@v1_places_bp.route("/attractions/nearby")
@require_api_key
def v1_attractions_nearby():
    """Ближайшие достопримечательности."""
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", default=5000, type=int)
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны", "code": "BAD_REQUEST"}), 400

    items = []
    for a in ATTRACTIONS:
        d = haversine(lat, lon, a["lat"], a["lon"])
        if d <= radius:
            item = dict(a)
            item["distance"] = int(d)
            item["distance_text"] = format_distance(d)
            items.append(item)
    items.sort(key=lambda x: x["distance"])
    return jsonify({"count": len(items), "attractions": items})
