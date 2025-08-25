from flask import Blueprint, render_template, session, redirect, url_for
from .. import socketio
from flask_socketio import join_room, emit

games_bp = Blueprint("games", __name__, url_prefix="/games")

@games_bp.route("/lobby")
def lobby():
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))
    return render_template("lobby.html", username=username)

@socketio.on("join_room")
def handle_join(data):
    username = session.get("username")
    room = data.get("room")
    if username and room:
        join_room(room)
        emit("user_joined", {"username": username}, room=room)

@socketio.on("send_message")
def handle_message(data):
    username = session.get("username")
    room = data.get("room")
    message = data.get("message")
    if username and room and message:
        emit("receive_message", {"username": username, "message": message}, room=room)
