# conundrum/routes.py
from flask import Blueprint, render_template

routes = Blueprint("routes", __name__)

@routes.route("/")
def home():
    """Render the homepage."""
    return render_template("home.html")
