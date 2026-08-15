"""API отзывов."""
from flask import Blueprint, request, jsonify

from services.reviews import (
    add_review, get_local_reviews, get_place_rating,
    FOURSQUARE_API_KEY,
)

reviews_bp = Blueprint("reviews", __name__)


@reviews_bp.route("/api/reviews")
def api_get_reviews():
    """Получить отзывы для места."""
    place_id = request.args.get("place_id")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    name = request.args.get("name")
    if not place_id and not (lat and lon):
        return jsonify({"error": "place_id или lat+lon обязательны"}), 400
    result = get_place_rating(place_id, lat, lon, name)
    return jsonify(result)


@reviews_bp.route("/api/reviews", methods=["POST"])
def api_add_review():
    """Добавить отзыв."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Нет данных"}), 400
    required = ["author_name", "rating", "text"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"Поле {f} обязательно"}), 400
    if not 1 <= data["rating"] <= 5:
        return jsonify({"error": "rating должен быть 1-5"}), 400
    review_id = add_review(
        place_id=data.get("place_id", ""),
        place_name=data.get("place_name", ""),
        lat=data.get("lat", 0),
        lon=data.get("lon", 0),
        author=data["author_name"],
        rating=int(data["rating"]),
        text=data["text"],
    )
    return jsonify({"id": review_id, "status": "added"})


@reviews_bp.route("/api/reviews/status")
def api_reviews_status():
    """Статус системы отзывов."""
    return jsonify({
        "foursquare_available": bool(FOURSQUARE_API_KEY),
        "foursquare_setup_url": "https://developer.foursquare.com",
        "local_reviews_count": len(get_local_reviews()),
        "message": (
            "Отзывы доступны через Foursquare API (нужен ключ) "
            "или через собственную базу (пользовательские отзывы)."
            if FOURSQUARE_API_KEY else
            "Foursquare API не настроен. "
            "Получите ключ на developer.foursquare.com и установите "
            "переменную окружения FOURSQUARE_API_KEY. "
            "Пока работают только пользовательские отзывы."
        ),
    })
