"""
认证蓝图
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from blueprints.auth import views  # noqa: F401
