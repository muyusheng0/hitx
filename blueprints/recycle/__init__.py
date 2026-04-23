from flask import Blueprint

recycle_bp = Blueprint('recycle', __name__)

from blueprints.recycle import views
