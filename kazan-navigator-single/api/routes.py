"""Маршруты: локальный NetworkX + OSRM."""
from flask import Blueprint, request, jsonify

from services.router import route_local, route_osrm

routes_bp = Blueprint("routes", __name__)


@routes_bp.route("/api/route")
def api_route():
    """Маршрут через OSRM (онлайн)."""
    start_lat = request.args.get("start_lat")
    start_lon = request.args.get("start_lon")
    end_lat = request.args.get("end_lat")
    end_lon = request.args.get("end_lon")
    profile = request.args.get("profile", "driving")
    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({"error": "Укажите все координаты"}), 400
    result = route_osrm(start_lat, start_lon, end_lat, end_lon, profile)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


@routes_bp.route("/api/local/route")
def api_local_route():
    """Локальный маршрут через NetworkX — без Docker и интернета."""
    try:
        start_lat = float(request.args.get("start_lat", 0))
        start_lon = float(request.args.get("start_lon", 0))
        end_lat = float(request.args.get("end_lat", 0))
        end_lon = float(request.args.get("end_lon", 0))
    except ValueError:
        return jsonify({"error": "Неверные координаты"}), 400
    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({"error": "Укажите все координаты"}), 400
    result = route_local(start_lat, start_lon, end_lat, end_lon)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)
