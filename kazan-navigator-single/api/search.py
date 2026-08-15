"""Поиск мест и реверс-геокодинг."""
from flask import Blueprint, request, jsonify

from services.geocoder import search, reverse_geocode, find_nearby, local_search

search_bp = Blueprint("search", __name__)


@search_bp.route("/api/search")
def api_search():
    """Комбинированный поиск: локальная БД + Nominatim."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    results = search(q)
    return jsonify(results)


@search_bp.route("/api/local/search")
def api_local_search():
    """Локальный поиск по SQLite FTS5 — без интернета."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    results = local_search(q)
    return jsonify(results)


@search_bp.route("/api/local/nearby")
def api_local_nearby():
    """Ближайшие места из локальной БД."""
    lat = float(request.args.get("lat", 0))
    lon = float(request.args.get("lon", 0))
    radius = int(request.args.get("radius", 1500))
    limit = int(request.args.get("limit", 30))
    category = request.args.get("category")
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны"}), 400
    items = find_nearby(lat, lon, radius, limit, category)
    return jsonify({"items": items, "count": len(items)})


@search_bp.route("/api/reverse")
def api_reverse():
    """Реверс-геокодинг: координаты → адрес."""
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны"}), 400
    result = reverse_geocode(lat, lon)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)
