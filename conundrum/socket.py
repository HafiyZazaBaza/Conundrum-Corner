# conundrum/socket.py
from flask_socketio import emit, join_room
from flask import request
from . import socketio
import random, string

lobbies = {}

def generate_lobby_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    try:
        max_players = int(data.get("maxPlayers", 8))
    except (ValueError, TypeError):
        max_players = 8

    if not username:
        emit("error_message", {"message": "Username required."}, room=request.sid)
        return

    lobby_code = generate_lobby_code()
    while lobby_code in lobbies:
        lobby_code = generate_lobby_code()

    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "max_players": max_players,
        "game_mode": None,  # host will choose later
    }

    join_room(lobby_code)

    emit("lobby_created", {
        "lobbyCode": lobby_code,
        "username": username,
        "maxPlayers": max_players,
    }, room=request.sid)

    emit("lobby_update", {
        "host": username,
        "players": lobbies[lobby_code]["players"]
    }, room=lobby_code)

@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if not username or not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Invalid join request."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if username not in lobby["players"]:
        if len(lobby["players"]) >= lobby["max_players"]:
            emit("error_message", {"message": "Lobby is full."}, room=request.sid)
            return
        lobby["players"].append(username)

    join_room(lobby_code)

    emit("lobby_joined", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": lobby["game_mode"],  # may be None
        "players": lobby["players"]
    }, room=request.sid)

    emit("lobby_update", {
        "host": lobby["host"],
        "players": lobby["players"]
    }, room=lobby_code)

@socketio.on("send_message")
def handle_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    message = data.get("message")

    if not lobby_code or lobby_code not in lobbies or not message:
        emit("error_message", {"message": "Invalid message."}, room=request.sid)
        return

    emit("receive_message", {"username": username, "message": message}, room=lobby_code)

@socketio.on("start_game")
def handle_start_game(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    mode = data.get("mode")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start."}, room=request.sid)
        return

    if not mode:
        emit("error_message", {"message": "Game mode required to start."}, room=request.sid)
        return

    # Save the chosen game mode
    lobby["game_mode"] = mode

    emit("game_started", {"lobbyCode": lobby_code, "mode": mode}, room=lobby_code)