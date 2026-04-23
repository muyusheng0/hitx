from flask import Blueprint
voice_bp = Blueprint('voice', __name__)
from blueprints.voice import views
