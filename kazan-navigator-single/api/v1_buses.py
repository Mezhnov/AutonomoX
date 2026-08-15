"""
API v1: Автобусы Казани.
Главный публичный API — как Яндекс.Транспорт.
"""
from flask import Blueprint, request, jsonify
from api.middleware import require_api_key
from services.bus_service import (
    BUS_ROUTES, get_real_routes, get_live_buses,
    reset_simulation, search_buses,
)

v1_buses_bp = Blueprint("v1_buses", __name__, url_prefix="/api/v1")


@v1_buses_bp.route("/buses")
@require_api_key
def v1_list_buses():
    """
    Список всех автобусных маршрутов Казани.

    **Параметры:**
    - `q` (опц.) — поиск по номеру/названию/остановке

    **Возвращает:** массив маршрутов с остановками
    """
    q = (request.args.get("q") or "").strip().lower()
    routes = search_buses(q) if q else BUS_ROUTES
    return jsonify({
        "count": len(routes),
        "routes": routes,
        "source": "kazan-navigator",
    })


@v1_buses_bp.route("/buses/<bus_id>")
@require_api_key
def v1_bus_detail(bus_id):
    """Детали конкретного маршрута."""
    for b in BUS_ROUTES:
        if b["id"] == bus_id:
            return jsonify(b)
    return jsonify({"error": "Маршрут не найден", "code": "NOT_FOUND"}), 404


@v1_buses_bp.route("/buses/real")
@require_api_key
def v1_real_buses():
    """
    Реальные маршруты из OpenStreetMap.
    Включает точные координаты пути и остановок.
    """
    result = get_real_routes()
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


@v1_buses_bp.route("/buses/live")
@require_api_key
def v1_live_buses():
    """
    🚌 GPS-позиции всех автобусов в реальном времени.

    **Возвращает:** массив с координатами, направлением, скоростью.
    Обновлять каждые 3-5 секунд.
    """
    route_id = request.args.get("route_id")
    result = get_live_buses(route_id)
    return jsonify(result)


@v1_buses_bp.route("/buses/live/<route_id>")
@require_api_key
def v1_live_bus_route(route_id):
    """GPS-позиции автобусов конкретного маршрута."""
    result = get_live_buses(route_id)
    return jsonify(result)


@v1_buses_bp.route("/buses/stops")
@require_api_key
def v1_bus_stops():
    """Все автобусные остановки Казани с координатами."""
    result = get_real_routes()
    if "error" in result:
        return jsonify(result), 503
    return jsonify({
        "count": result.get("stops_count", 0),
        "stops": result.get("stops", []),
    })


@v1_buses_bp.route("/buses/nearby")
@require_api_key
def v1_buses_nearby():
    """
    Ближайшие остановки к точке.

    **Параметры:**
    - `lat` (обяз.) — широта
    - `lon` (обяз.) — долгота
    - `radius` (опц., по умолч. 500) — радиус в метрах
    """
    from utils import haversine, format_distance

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", default=500, type=int)
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны", "code": "BAD_REQUEST"}), 400

    routes_data = get_real_routes()
    if "error" in routes_data:
        return jsonify(routes_data), 503

    stops = []
    for stop in routes_data.get("stops", []):
        d = haversine(lat, lon, stop["lat"], stop["lon"])
        if d <= radius:
            stop_copy = dict(stop)
            stop_copy["distance"] = int(d)
            stop_copy["distance_text"] = format_distance(d)
            stops.append(stop_copy)

    stops.sort(key=lambda x: x["distance"])
    return jsonify({
        "count": len(stops),
        "stops": stops[:20],
        "search_center": {"lat": lat, "lon": lon, "radius": radius},
    })
