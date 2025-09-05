# conundrum/games/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from .. import socketio
from flask_socketio import join_room, leave_room, emit
from uuid import uuid4

# Import game classes
from .reverse_guessing import ReverseGuessingGame
from .bad_advice_hotline import BadAdviceGame
from .emoji_translation import EmojiTranslationGame
from .obviously_lies import ObviouslyLiesGame

games_bp = Blueprint("games", __name__, url_prefix="/games")

# Game instances
reverse_game = ReverseGuessingGame()
bad_advice_game = BadAdviceGame()
emoji_game = EmojiTranslationGame()
lies_game = ObviouslyLiesGame()

# Track connected players: { sid: {"username": ..., "room": ...} }
players = {}

# Track lobbies: { lobby_code: {"host": ..., "players": []} }
lobbies = {}

# --------------------------
# Home & Lobby Routes
# --------------------------

@games_bp.route("/lobby")
def lobby():
    username = request.args.get("username")
    lobby_code = request.args.get("lobby")
    game_mode = request.args.get("mode")

    if not username or not lobby_code or not game_mode:
        return redirect(url_for("home"))

    session["username"] = username
    session["lobby"] = lobby_code
    session["mode"] = game_mode

    return render_template(
        "lobby.html",
        username=username,
        lobby_code=lobby_code,
        game_mode=game_mode
    )

# --------------------------
# Socket Events: Lobby
# --------------------------

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    game_mode = data.get("gameMode")
    max_players = int(data.get("maxPlayers", 8))

    lobby_code = str(uuid4())[:4].upper()  # 4-char lobby code
    lobbies[lobby_code] = {"host": username, "players": [username], "mode": game_mode, "max": max_players}

    emit("lobby_created", {"username": username, "lobbyCode": lobby_code, "gameMode": game_mode}, room=request.sid)

@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found"}, room=request.sid)
        return

    if len(lobbies[lobby_code]["players"]) >= lobbies[lobby_code]["max"]:
        emit("error_message", {"message": "Lobby is full"}, room=request.sid)
        return

    lobbies[lobby_code]["players"].append(username)
    join_room(lobby_code)

    # Notify joining player
    emit("lobby_joined", {"username": username, "lobbyCode": lobby_code, "gameMode": lobbies[lobby_code]["mode"]}, room=request.sid)

    # Update everyone in lobby
    emit("user_list", lobbies[lobby_code]["players"], room=lobby_code)

# Chat system
@socketio.on("send_message")
def handle_message(data):
    room = session.get("lobby")
    username = session.get("username")
    message = data.get("message")

    if room and username and message:
        emit("receive_message", {"username": username, "message": message}, room=room)
