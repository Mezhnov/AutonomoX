"""API blueprint-ы."""
from .search import search_bp
from .routes import routes_bp
from .buses import buses_bp
from .attractions import attractions_bp
from .favorites import favorites_bp
from .weather import weather_bp
from .health import health_bp
from .reviews import reviews_bp

__all__ = ["search_bp", "routes_bp", "buses_bp", "attractions_bp",
           "favorites_bp", "weather_bp", "health_bp", "reviews_bp"]
