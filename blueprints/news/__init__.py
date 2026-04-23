"""
新闻/校友/验证码蓝图
"""

from flask import Blueprint

news_bp = Blueprint('news', __name__)

from blueprints.news import views  # noqa: F401
