from flask import Blueprint

txl_bp = Blueprint('txl', __name__)

from blueprints.txl import views
