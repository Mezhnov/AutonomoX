"""
Swagger UI / OpenAPI документация.
Показывает красивую интерактивную документацию на /api/docs.
"""
from flask import Blueprint, jsonify, Response

docs_bp = Blueprint("docs", __name__)


OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Казань Навигатор API",
        "description": """
## 🚌 Публичный API Казани

Как Яндекс.Карты и 2GIS, но для Казани.

### Возможности:
- **🚌 Автобусы**: реальные маршруты, остановки, GPS-позиции в реальном времени
- **📍 Места**: 19 763 мест (кафе, рестораны, аптеки, АЗС, магазины)
- **🛣 Маршруты**: локальный роутинг (NetworkX) + OSRM
- **🏛 Достопримечательности**: 19 главных мест Казани
- **⭐ Отзывы**: рейтинги и пользовательские отзывы
- **🌤 Погода**: текущая погода в Казани

### Быстрый старт:
1. Используйте демо-ключ: `kzn_demo_key_2024`
2. Передавайте в header: `X-API-Key: kzn_demo_key_2024`
3. Лимит: 100 запросов/мин

### Получить свой ключ:
```
POST /api/v1/keys/register
{
  "name": "Мой проект",
  "email": "me@example.com"
}
```
        """,
        "version": "1.0.0",
        "contact": {
            "name": "Казань Навигатор",
            "url": "https://kazan-navigator.ru",
        },
        "license": {"name": "MIT"},
    },
    "servers": [
        {"url": "/", "description": "Текущий сервер"},
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API ключ. Демо: kzn_demo_key_2024",
            }
        }
    },
    "security": [{"ApiKeyAuth": []}],
    "paths": {},
    "tags": [
        {"name": "Автобусы", "description": "Маршруты, остановки, GPS"},
        {"name": "Места", "description": "Поиск, категории, nearby"},
        {"name": "Маршруты", "description": "Построение маршрутов"},
        {"name": "Отзывы", "description": "Рейтинги и отзывы"},
        {"name": "Геокодинг", "description": "Адрес ↔ координаты"},
        {"name": "Ключи", "description": "Управление API-ключами"},
    ],
}

# Добавляем paths вручную (для красоты)
OPENAPI_SPEC["paths"] = {
    "/api/v1/buses": {
        "get": {
            "tags": ["Автобусы"],
            "summary": "Список всех автобусных маршрутов",
            "parameters": [
                {"name": "q", "in": "query", "schema": {"type": "string"},
                 "description": "Поиск по номеру/названию/остановке"},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/buses/live": {
        "get": {
            "tags": ["Автобусы"],
            "summary": "🚌 GPS-позиции всех автобусов в реальном времени",
            "description": "Возвращает массив с координатами всех активных автобусов. Обновлять каждые 3-5 секунд.",
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/buses/nearby": {
        "get": {
            "tags": ["Автобусы"],
            "summary": "Ближайшие автобусные остановки",
            "parameters": [
                {"name": "lat", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "lon", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "radius", "in": "query", "schema": {"type": "integer", "default": 500}},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/places": {
        "get": {
            "tags": ["Места"],
            "summary": "Поиск мест в Казани",
            "parameters": [
                {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                {"name": "category", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/places/nearby": {
        "get": {
            "tags": ["Места"],
            "summary": "Ближайшие места к точке",
            "parameters": [
                {"name": "lat", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "lon", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "radius", "in": "query", "schema": {"type": "integer", "default": 1500}},
                {"name": "category", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/routes": {
        "get": {
            "tags": ["Маршруты"],
            "summary": "Построить маршрут между двумя точками",
            "parameters": [
                {"name": "start_lat", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "start_lon", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "end_lat", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "end_lon", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "profile", "in": "query", "schema": {"type": "string", "default": "driving"},
                 "enum": ["driving", "foot", "cycling"]},
                {"name": "engine", "in": "query", "schema": {"type": "string", "default": "local"},
                 "enum": ["local", "osrm"]},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/geocode": {
        "get": {
            "tags": ["Геокодинг"],
            "summary": "Геокодинг: адрес → координаты",
            "parameters": [
                {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/reverse-geocode": {
        "get": {
            "tags": ["Геокодинг"],
            "summary": "Реверс-геокодинг: координаты → адрес",
            "parameters": [
                {"name": "lat", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "lon", "in": "query", "required": True, "schema": {"type": "number"}},
            ],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/reviews": {
        "get": {
            "tags": ["Отзывы"],
            "summary": "Получить отзывы и рейтинг места",
            "parameters": [
                {"name": "place_id", "in": "query", "schema": {"type": "string"}},
                {"name": "lat", "in": "query", "schema": {"type": "number"}},
                {"name": "lon", "in": "query", "schema": {"type": "number"}},
            ],
            "responses": {"200": {"description": "OK"}},
        },
        "post": {
            "tags": ["Отзывы"],
            "summary": "Добавить отзыв",
            "requestBody": {
                "content": {"application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "author_name": {"type": "string"},
                            "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                            "text": {"type": "string"},
                            "place_name": {"type": "string"},
                            "lat": {"type": "number"},
                            "lon": {"type": "number"},
                        }
                    }
                }}
            },
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/attractions": {
        "get": {
            "tags": ["Места"],
            "summary": "Достопримечательности Казани",
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/keys/register": {
        "post": {
            "tags": ["Ключи"],
            "summary": "Получить API-ключ",
            "description": "Публичный endpoint. Создаёт новый API-ключ.",
            "security": [],
            "requestBody": {
                "content": {"application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Название проекта"},
                            "email": {"type": "string"},
                            "description": {"type": "string"},
                            "tier": {"type": "string", "enum": ["free", "pro", "business"]},
                        }
                    }
                }}
            },
            "responses": {"200": {"description": "API ключ создан"}},
        }
    },
    "/api/v1/stats": {
        "get": {
            "tags": ["Ключи"],
            "summary": "Общая статистика API",
            "security": [],
            "responses": {"200": {"description": "OK"}},
        }
    },
    "/api/v1/health": {
        "get": {
            "tags": ["Ключи"],
            "summary": "Health check",
            "security": [],
            "responses": {"200": {"description": "OK"}},
        }
    },
}


SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Казань Навигатор API — Documentation</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
<style>
  body { margin: 0; }
  .topbar { display: none; }
</style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
window.onload = function() {
  window.ui = SwaggerUIBundle({
    url: "/api/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis],
    layout: "BaseLayout",
    defaultModelsExpandDepth: -1,
    docExpansion: "list",
  });
};
</script>
</body>
</html>"""


@docs_bp.route("/api/docs")
def api_docs():
    """Swagger UI."""
    return Response(SWAGGER_HTML, content_type="text/html; charset=utf-8")


@docs_bp.route("/api/openapi.json")
def openapi_json():
    """OpenAPI 3.0 спецификация."""
    return jsonify(OPENAPI_SPEC)
