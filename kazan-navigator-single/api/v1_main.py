"""
API v1: Маршруты, геокодинг, отзывы, регистрация ключей, статистика.
"""
from flask import Blueprint, request, jsonify
from api.middleware import require_api_key
from services.router import route_local, route_osrm
from services.geocoder import search as geocode_search, reverse_geocode
from services.reviews import (
    add_review, get_local_reviews, get_place_rating,
    FOURSQUARE_API_KEY,
)
from services.api_keys import (
    create_api_key, get_api_stats, list_api_keys, validate_api_key,
)
from services.bus_service import BUS_ROUTES
from api.attractions import ATTRACTIONS

v1_main_bp = Blueprint("v1_main", __name__, url_prefix="/api/v1")


# ===== МАРШРУТЫ =====
@v1_main_bp.route("/routes")
@require_api_key
def v1_routes():
    """
    Построение маршрута между двумя точками.

    **Параметры:**
    - `start_lat`, `start_lon` (обяз.) — точка старта
    - `end_lat`, `end_lon` (обяз.) — точка финиша
    - `profile` (опц., по умолч. driving) — driving, foot, cycling
    - `engine` (опц.) — local (NetworkX) или osrm (онлайн)
    """
    start_lat = request.args.get("start_lat", type=float)
    start_lon = request.args.get("start_lon", type=float)
    end_lat = request.args.get("end_lat", type=float)
    end_lon = request.args.get("end_lon", type=float)
    profile = request.args.get("profile", "driving")
    engine = request.args.get("engine", "local")

    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({"error": "Укажите start_lat, start_lon, end_lat, end_lon",
                        "code": "BAD_REQUEST"}), 400

    if engine == "local" and profile == "driving":
        result = route_local(start_lat, start_lon, end_lat, end_lon)
    else:
        result = route_osrm(start_lat, start_lon, end_lat, end_lon, profile)

    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


# ===== ГЕОКОДИНГ =====
@v1_main_bp.route("/geocode")
@require_api_key
def v1_geocode():
    """
    Геокодинг: адрес → координаты.

    **Параметры:**
    - `q` (обяз.) — адрес или название места
    - `limit` (опц., макс. 20)
    """
    q = (request.args.get("q") or "").strip()
    limit = min(request.args.get("limit", default=10, type=int), 20)
    if len(q) < 2:
        return jsonify({"error": "Минимум 2 символа", "code": "BAD_REQUEST"}), 400
    results = geocode_search(q, limit=limit)
    return jsonify({"query": q, "count": len(results), "results": results})


@v1_main_bp.route("/reverse-geocode")
@require_api_key
def v1_reverse_geocode():
    """
    Реверс-геокодинг: координаты → адрес.

    **Параметры:**
    - `lat`, `lon` (обяз.)
    """
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны", "code": "BAD_REQUEST"}), 400
    result = reverse_geocode(lat, lon)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


# ===== ОТЗЫВЫ =====
@v1_main_bp.route("/reviews")
@require_api_key
def v1_reviews():
    """
    Получить отзывы и рейтинг места.

    **Параметры:**
    - `place_id` (опц.) — ID места
    - `lat`, `lon` (опц.) — координаты места
    - `name` (опц.) — название для поиска в Foursquare
    """
    place_id = request.args.get("place_id")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    name = request.args.get("name")
    if not place_id and not (lat and lon):
        return jsonify({"error": "place_id или lat+lon обязательны", "code": "BAD_REQUEST"}), 400
    result = get_place_rating(place_id, lat, lon, name)
    return jsonify(result)


@v1_main_bp.route("/reviews", methods=["POST"])
@require_api_key
def v1_add_review():
    """
    Добавить отзыв.

    **Body (JSON):**
    - `author_name` (обяз.) — имя автора
    - `rating` (обяз., 1-5) — оценка
    - `text` (обяз.) — текст отзыва
    - `place_id`, `place_name`, `lat`, `lon` — место
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Нет данных", "code": "BAD_REQUEST"}), 400
    required = ["author_name", "rating", "text"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Поле {f} обязательно", "code": "BAD_REQUEST"}), 400
    if not 1 <= data["rating"] <= 5:
        return jsonify({"error": "rating должен быть 1-5", "code": "BAD_REQUEST"}), 400
    review_id = add_review(
        place_id=data.get("place_id", ""),
        place_name=data.get("place_name", ""),
        lat=data.get("lat", 0),
        lon=data.get("lon", 0),
        author=data["author_name"],
        rating=int(data["rating"]),
        text=data["text"],
    )
    return jsonify({"id": review_id, "status": "added", "message": "Отзыв добавлен"})


# ===== РЕГИСТРАЦИЯ API КЛЮЧЕЙ =====
@v1_main_bp.route("/keys/register", methods=["POST"])
def v1_register_key():
    """
    Регистрация нового API-ключа.
    Не требует ключа — публичный endpoint.

    **Body (JSON):**
    - `name` (обяз.) — название проекта
    - `email` (опц.) — для связи
    - `description` (опц.) — описание проекта
    - `tier` (опц., по умолч. free) — free, pro, business
    """
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "name обязательно", "code": "BAD_REQUEST"}), 400
    result = create_api_key(
        name=data["name"],
        email=data.get("email"),
        description=data.get("description"),
        tier=data.get("tier", "free"),
    )
    return jsonify({
        **result,
        "message": "API ключ создан. Используйте его в header: X-API-Key",
        "documentation": "/api/docs",
        "example": "curl -H 'X-API-Key: " + result["key"] + "' http://localhost:5000/api/v1/buses",
    })


@v1_main_bp.route("/keys/verify")
def v1_verify_key():
    """Проверить API-ключ."""
    api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
    key_data, error = validate_api_key(api_key)
    if error:
        return jsonify({"valid": False, "error": error}), 401
    return jsonify({"valid": True, "key_data": {
        "name": key_data["name"],
        "tier": key_data["tier"],
        "requests_limit": key_data["requests_limit"],
    }})


@v1_main_bp.route("/keys/stats")
@require_api_key
def v1_my_stats():
    """Статистика использования текущего API-ключа."""
    from flask import g
    stats = get_api_stats(g.api_key_data["id"])
    return jsonify({
        "api_key": {
            "name": g.api_key_data["name"],
            "tier": g.api_key_data["tier"],
            "requests_limit_per_min": g.api_key_data["requests_limit"],
        },
        "usage": stats,
    })


# ===== СТАТИСТИКА API =====
@v1_main_bp.route("/stats")
def v1_api_stats():
    """Общая статистика API (без ключа)."""
    stats = get_api_stats()
    return jsonify({
        **stats,
        "data": {
            "places_count": "19 763 мест в Казани",
            "bus_routes": len(BUS_ROUTES) + 105,  # справочные + реальные
            "attractions": len(ATTRACTIONS),
            "road_graph_nodes": 109323,
            "road_graph_edges": 223514,
        },
        "endpoints": [
            "GET /api/v1/buses",
            "GET /api/v1/buses/live",
            "GET /api/v1/places?q=",
            "GET /api/v1/places/nearby?lat=&lon=",
            "GET /api/v1/routes?start_lat=&start_lon=&end_lat=&end_lon=",
            "GET /api/v1/geocode?q=",
            "GET /api/v1/reviews?lat=&lon=",
            "POST /api/v1/reviews",
            "GET /api/v1/attractions",
        ],
    })


@v1_main_bp.route("/health")
def v1_health():
    """Health check API v1."""
    return jsonify({
        "status": "ok",
        "api_version": "v1",
        "service": "Казань Навигатор Public API",
        "documentation": "/api/docs",
        "demo_key": "kzn_demo_key_2024",
    })
