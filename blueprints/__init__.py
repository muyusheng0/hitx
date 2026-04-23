"""
蓝图注册模块
"""

from blueprints.news import news_bp
from blueprints.location import location_bp


BLUEPRINTS = [
    news_bp,
    location_bp,
]


def register_blueprints(app):
    """注册所有蓝图到 Flask 应用"""
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
