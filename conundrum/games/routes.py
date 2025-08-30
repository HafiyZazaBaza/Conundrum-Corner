import socket
from flask import Blueprint, request
from flask_socketio import emit, join_room
import random
import string

games_bp = Blueprint("games", __name__, url_prefix="/games")

# Temporary in-memory lobby storage
lobbies = {}  # lobby_code: { "host": username, "players": {username: sid}, "max_players": int, "game_mode": str }

# ------------------ Create Lobby ------------------
@games_bp.route("/")
def index():
    return "Games Blueprint active"

@socket.io.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    max_players = data.get("maxPlayers")
    game_mode = data.get("gameMode")

    # Generate a random 4-digit lobby code
    lobby_code = "".join(random.choices(string.digits, k=4))

    # Store lobby info
    lobbies[lobby_code] = {
        "host": username,
        "players": {username: request.sid},
        "max_players": max_players,
        "game_mode": game_mode
    }

    join_room(lobby_code)
    emit("lobby_created", {"lobbyCode": lobby_code, "gameMode": game_mode, "username": username}, room=request.sid)

# ------------------ Join Lobby ------------------
@socket.io.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]

    # Check if lobby is full
    if len(lobby["players"]) >= int(lobby["max_players"]):
        emit("error_message", {"message": "Lobby is full."}, room=request.sid)
        return

    # Add player
    lobby["players"][username] = request.sid
    join_room(lobby_code)

    emit("lobby_joined", {"lobbyCode": lobby_code, "username": username}, room=lobby_code)
