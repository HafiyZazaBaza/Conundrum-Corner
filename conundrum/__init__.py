from flask import Flask, session, redirect, url_for, render_template, request
from flask_socketio import SocketIO

socketio = SocketIO()  # global SocketIO object

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "super-secret-key"

    # Register blueprints
    from .games.routes import games_bp
    app.register_blueprint(games_bp)

    # Home route for temporary username
    @app.route("/", methods=["GET", "POST"])
    def home():
        if request.method == "POST":
            username = request.form.get("username")
            if not username:
                # Auto-generate temporary username
                import random, string
                username = "User_" + "".join(random.choices(string.ascii_letters + string.digits, k=4))
            session["username"] = username
            return redirect(url_for("games.lobby"))
        return render_template("home.html")

    socketio.init_app(app)
    return app
