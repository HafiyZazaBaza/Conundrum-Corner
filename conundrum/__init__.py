# conundrum/__init__.py
from flask import Flask, render_template
from flask_socketio import SocketIO

socketio = SocketIO()  # global SocketIO object

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",  # ✅ FIXED
        static_folder="static"        # ✅ FIXED
    )
    app.config['SECRET_KEY'] = "super-secret-key"

    # Register blueprints
    from .games.routes import games_bp
    app.register_blueprint(games_bp)

    # Import socket events so they register
    from . import socket  

    # Home route (landing page)
    @app.route("/", methods=["GET"])
    def home():
        return render_template("home.html")

    socketio.init_app(app)
    return app
