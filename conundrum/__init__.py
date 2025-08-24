from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "supersecret"  # put in .env later

    socketio.init_app(app)

    # Register blueprints (auth, games, lobby, etc.)
    from .network.server import network_bp
    app.register_blueprint(network_bp)

    return app
