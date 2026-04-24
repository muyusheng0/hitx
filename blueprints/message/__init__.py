"""
留言/评论/点赞 蓝图
"""

from flask import Blueprint

message_bp = Blueprint('message', __name__)

from blueprints.message import views  # noqa: F401
