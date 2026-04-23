"""
地理位置蓝图
"""

from flask import Blueprint

location_bp = Blueprint('location', __name__)

from blueprints.location import views  # noqa: F401
