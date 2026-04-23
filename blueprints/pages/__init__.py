from flask import Blueprint
pages_bp = Blueprint('pages', __name__)
from blueprints.pages import views
