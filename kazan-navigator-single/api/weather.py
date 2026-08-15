"""Погода и POI."""
from flask import Blueprint, request, jsonify

from services.weather import get_weather
from services.poi import get_pois

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/api/weather")
def api_weather():
    """Текущая погода в Казани."""
    result = get_weather()
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


@weather_bp.route("/api/pois")
def api_pois():
    """POI по категории из OSM."""
    category = request.args.get("category", "food")
    result = get_pois(category)
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)
