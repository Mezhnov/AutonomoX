"""
====================================================================
  КАЗАНЬ НАВИГАТОР 4.0 — МОДУЛЬНАЯ АРХИТЕКТУРА
====================================================================
  Flask приложение с модульной структурой:
  
  app.py              — точка входа, регистрация blueprints
  config.py           — конфигурация
  extensions.py       — db, cache
  utils.py            — утилиты (геометрия, форматирование)
  api/                — HTTP эндпоинты (blueprints)
  services/           — бизнес-логика
  templates/          — HTML шаблоны
  static/             — CSS, JS, шрифты, данные
  
  Запуск:  python3 app.py --port 5000
  Открыть: http://localhost:5000
====================================================================
"""

import argparse
from pathlib import Path
from flask import Flask, send_from_directory, send_file

from config import BASE_DIR, DEBUG, HOST, PORT, SECRET_KEY
from extensions import cache
from api import (search_bp, routes_bp, buses_bp, attractions_bp,
                 favorites_bp, weather_bp, health_bp, reviews_bp)
from api.v1_buses import v1_buses_bp
from api.v1_places import v1_places_bp
from api.v1_main import v1_main_bp
from api.docs import docs_bp


def create_app():
    """Фабрика приложения."""
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG

    # Регистрация API blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(buses_bp)
    app.register_blueprint(attractions_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(reviews_bp)

    # v1 Public API (как Яндекс.Карты / 2GIS)
    app.register_blueprint(v1_buses_bp)
    app.register_blueprint(v1_places_bp)
    app.register_blueprint(v1_main_bp)
    app.register_blueprint(docs_bp)  # Swagger UI на /api/docs

    # CORS для разработки
    if DEBUG:
        try:
            from flask_cors import CORS
            CORS(app)
        except ImportError:
            pass

    # --- Статические файлы ---
    @app.route("/static/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(str(BASE_DIR / "static" / "css"), filename)

    @app.route("/static/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(str(BASE_DIR / "static" / "js"), filename)

    @app.route("/static/webfonts/<path:filename>")
    def serve_webfonts(filename):
        return send_from_directory(str(BASE_DIR / "static" / "webfonts"), filename,
                                   mimetype="font/woff2")

    @app.route("/static/img/<path:filename>")
    def serve_img(filename):
        return send_from_directory(str(BASE_DIR / "static" / "img"), filename)

    @app.route("/static/data/<path:filename>")
    def serve_data(filename):
        return send_from_directory(str(BASE_DIR / "static" / "data"), filename)

    # --- Главная страница ---
    @app.route("/")
    def index():
        return send_file(str(BASE_DIR / "templates" / "index.html"))

    return app


# Глобальное приложение для gunicorn
app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Казань Навигатор 4.0")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--debug", action="store_true", default=DEBUG)
    args = parser.parse_args()

    print("=" * 60)
    print("  Казань Навигатор 4.0 — модульная архитектура")
    print(f"  http://localhost:{args.port}")
    print(f"  Структура: api/ services/ templates/ static/")
    print(f"  API: /api/health, /api/local/search, /api/local/route")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug,
            use_reloader=args.debug)
