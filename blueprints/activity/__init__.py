from flask import Blueprint
activity_bp = Blueprint('activity', __name__)
from blueprints.activity import views
