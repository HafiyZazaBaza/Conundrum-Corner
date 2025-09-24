# conundrum/__init__.py
from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    app.config["SECRET_KEY"] = "super-secret-key"

    # --- Register blueprints ---
    from .routes import routes        # main site routes (homepage, etc.)
    from .games.routes import games_bp  # game-related routes

    app.register_blueprint(routes)
    app.register_blueprint(games_bp)

    # --- Import socket events so they register ---
    from . import socket  

    socketio.init_app(app)
    return app
