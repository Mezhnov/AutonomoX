"""Достопримечательности Казани."""
from flask import Blueprint, request, jsonify

from utils import haversine, format_distance

attractions_bp = Blueprint("attractions", __name__)


ATTRACTIONS = [
    # Казанский Кремль
    {"id": "kreml", "name": "Казанский Кремль", "category": "history",
     "lat": 55.7987, "lon": 49.1063, "address": "площадь Тысячелетия, 1",
     "icon": "landmark",
     "description": "Объект Всемирного наследия ЮНЕСКО. Построен в XVI-XVIII веках.",
     "rating": 4.9, "work_hours": "08:00-20:00", "free": True},
    {"id": "kul_sharif", "name": "Мечеть Кул-Шариф", "category": "religion",
     "lat": 55.7990, "lon": 49.1056, "address": "Казанский Кремль", "icon": "mosque",
     "description": "Одна из крупнейших мечетей Европы. Построена в 2005 году.",
     "rating": 4.9, "work_hours": "09:00-19:30", "free": True},
    {"id": "spasskaya", "name": "Спасская башня", "category": "history",
     "lat": 55.7997, "lon": 49.1064, "address": "Казанский Кремль", "icon": "tower-cell",
     "description": "Главный въезд в Кремль. Построена в 1556-1562 годах.",
     "rating": 4.8, "work_hours": "Круглосуточно", "free": True},
    {"id": "syuyumbike", "name": "Башня Сююмбике", "category": "history",
     "lat": 55.7995, "lon": 49.1058, "address": "Казанский Кремль",
     "icon": "tower-observation",
     "description": "Наклонная башня высотой 58 метров. Отклонение — 1.98 метра.",
     "rating": 4.8, "work_hours": "Круглосуточно", "free": True},
    {"id": "blagoveshchensky", "name": "Благовещенский собор", "category": "religion",
     "lat": 55.7989, "lon": 49.1067, "address": "Казанский Кремль", "icon": "church",
     "description": "Старейшее каменное здание Казани (1561-1562).",
     "rating": 4.8, "work_hours": "08:00-19:00", "free": True},

    # Улицы
    {"id": "bauman", "name": "Улица Баумана", "category": "street",
     "lat": 55.7884, "lon": 49.1215, "address": "улица Баумана", "icon": "road",
     "description": "Главная пешеходная улица Казани длиной 1885 метров.",
     "rating": 4.8, "work_hours": "Круглосуточно", "free": True},
    {"id": "peterburgskaya", "name": "Улица Петербургская", "category": "street",
     "lat": 55.7922, "lon": 49.1185, "address": "улица Петербургская", "icon": "road",
     "description": "Пешеходная улица в стиле северной столицы.",
     "rating": 4.6, "work_hours": "Круглосуточно", "free": True},

    # Парки
    {"id": "kaban", "name": "Озеро Кабан", "category": "nature",
     "lat": 55.7702, "lon": 49.1307, "address": "озеро Кабан", "icon": "water",
     "description": "Система из трёх озёр. Площадь — 1,86 км².",
     "rating": 4.7, "work_hours": "Круглосуточно", "free": True},
    {"id": "gorky_park", "name": "Парк Горького", "category": "park",
     "lat": 55.7965, "lon": 49.1506, "address": "улица Бондаренко, 1", "icon": "tree",
     "description": "Центральный парк культуры и отдыха. Основан в 1934 году.",
     "rating": 4.5, "work_hours": "09:00-23:00", "free": True},
    {"id": "victory_park", "name": "Парк Победы", "category": "park",
     "lat": 55.8015, "lon": 49.1829, "address": "улица Муса Джалиля", "icon": "monument",
     "description": "Мемориальный парк, посвящённый Победе в ВОВ.",
     "rating": 4.6, "work_hours": "Круглосуточно", "free": True},

    # Архитектура
    {"id": "dvorets_zemledeleltsev", "name": "Дворец земледельцев", "category": "architecture",
     "lat": 55.7889, "lon": 49.1094, "address": "улица Карла Маркса, 6/39",
     "icon": "building-columns",
     "description": "Дворцовый комплекс в стиле ампир, построен в 1845 году.",
     "rating": 4.7, "work_hours": "Снаружи круглосуточно", "free": True},
    {"id": "kazan_family", "name": "Центр семьи «Казан»", "category": "modern",
     "lat": 55.7898, "lon": 49.1152, "address": "улица Салимжанова, 2В", "icon": "building",
     "description": "Современный центр ЗАГС в форме большой казанской сковороды.",
     "rating": 4.5, "work_hours": "09:00-21:00", "free": True},

    # Памятники
    {"id": "kot_kazansky", "name": "Памятник Коту Казанскому", "category": "monument",
     "lat": 55.7883, "lon": 49.1215, "address": "улица Баумана", "icon": "cat",
     "description": "Бронзовый памятник коту весом 4 тонны, установлен в 2009 году.",
     "rating": 4.7, "work_hours": "Круглосуточно", "free": True},
    {"id": "ekaterina_carriage", "name": "Карета Екатерины II", "category": "monument",
     "lat": 55.7878, "lon": 49.1221, "address": "улица Баумана", "icon": "horse",
     "description": "Бронзовая карета императрицы Екатерины II.",
     "rating": 4.6, "work_hours": "Круглосуточно", "free": True},

    # Музеи
    {"id": "nacionalny_muzey", "name": "Национальный музей РТ", "category": "museum",
     "lat": 55.7892, "lon": 49.1087, "address": "улица Кремлёвская, 2", "icon": "landmark",
     "description": "Крупнейший музей Татарстана. Основан в 1894 году.",
     "rating": 4.7, "work_hours": "10:00-18:00, кроме понедельника", "free": False},
    {"id": "chakchak_museum", "name": "Музей чак-чака", "category": "museum",
     "lat": 55.7817, "lon": 49.1133, "address": "улица Парижской Коммуны, 18а",
     "icon": "cookie-bite",
     "description": "Единственный в мире музей чак-чака.",
     "rating": 4.6, "work_hours": "10:00-20:00", "free": False},

    # Религия
    {"id": "al_marjani", "name": "Мечеть Аль-Марджани", "category": "religion",
     "lat": 55.7815, "lon": 49.1176, "address": "улица Каюма Насыри, 17", "icon": "mosque",
     "description": "Первая каменная мечеть Казани после взятия города Иваном Грозным.",
     "rating": 4.7, "work_hours": "05:00-21:00", "free": True},

    # Развлечения
    {"id": "aquapark_riviera", "name": "Аквапарк Ривьера", "category": "entertainment",
     "lat": 55.7990, "lon": 49.1166, "address": "улица Фатыха Амирхана, 1",
     "icon": "water-ladder",
     "description": "Крупнейший аквапарк Поволжья. Открыт в 2006 году.",
     "rating": 4.5, "work_hours": "10:00-23:00", "free": False},
    {"id": "circus", "name": "Казанский цирк", "category": "entertainment",
     "lat": 55.7997, "lon": 49.1073, "address": "улица Астрономическая, 2", "icon": "tent",
     "description": "Цирк в форме НЛО, построен в 1967 году.",
     "rating": 4.6, "work_hours": "По афише", "free": False},
]


@attractions_bp.route("/api/attractions")
def api_attractions():
    """Список достопримечательностей с фильтром по категории."""
    category = request.args.get("category")
    items = ATTRACTIONS
    if category and category != "all":
        items = [a for a in ATTRACTIONS if a["category"] == category]
    return jsonify({"count": len(items), "items": items})


@attractions_bp.route("/api/attractions/<attraction_id>")
def api_attraction_detail(attraction_id):
    """Детали достопримечательности."""
    for a in ATTRACTIONS:
        if a["id"] == attraction_id:
            return jsonify(a)
    return jsonify({"error": "Не найдено"}), 404


@attractions_bp.route("/api/attractions/nearby")
def api_attractions_nearby():
    """Ближайшие достопримечательности."""
    lat = float(request.args.get("lat", 0))
    lon = float(request.args.get("lon", 0))
    radius = int(request.args.get("radius", 5000))
    if not lat or not lon:
        return jsonify({"error": "lat и lon обязательны"}), 400
    items = []
    for a in ATTRACTIONS:
        d = haversine(lat, lon, a["lat"], a["lon"])
        if d <= radius:
            item = dict(a)
            item["distance"] = int(d)
            item["distance_text"] = format_distance(d)
            items.append(item)
    items.sort(key=lambda x: x["distance"])
    return jsonify({"items": items, "count": len(items)})
