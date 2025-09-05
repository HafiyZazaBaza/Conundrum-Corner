# conundrum/socket.py
from flask_socketio import emit, join_room
from flask import request
from . import socketio
import random
import string

# In-memory lobby store
lobbies = {}

# Utility function: generate random lobby codes
def generate_lobby_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))

# ----------------- SOCKET EVENTS -----------------

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    try:
        max_players = int(data.get("maxPlayers"))
    except (ValueError, TypeError):
        max_players = 4  # fallback default

    game_mode = data.get("gameMode")

    # Validation
    if not username or not game_mode:
        emit("error_message", {"message": "Invalid data. Username and game mode are required."})
        return
    if max_players < 1 or max_players > 10:
        emit("error_message", {"message": "Max players must be between 1 and 10."})
        return

    # Generate unique lobby code
    lobby_code = generate_lobby_code()
    while lobby_code in lobbies:
        lobby_code = generate_lobby_code()

    # Save lobby info
    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "max_players": max_players,
        "game_mode": game_mode,
    }

    join_room(lobby_code)

    # Send confirmation to creator
    emit("lobby_created", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": game_mode,
        "maxPlayers": max_players,
    })

    # Update all players in this room
    emit("lobby_update", {
        "host": username,
        "players": lobbies[lobby_code]["players"]
    }, room=lobby_code)

@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    # Validation
    if not username or not lobby_code:
        emit("error_message", {"message": "Invalid join request."})
        return
    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."})
        return

    lobby = lobbies[lobby_code]
    if len(lobby["players"]) >= lobby["max_players"]:
        emit("error_message", {"message": "Lobby is full."})
        return

    # Add player
    lobby["players"].append(username)
    join_room(lobby_code)

    # Notify joining player
    emit("lobby_joined", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": lobby["game_mode"],
        "players": lobby["players"],
    })

    # Notify all players with updated list
    emit("lobby_update", {
        "host": lobby["host"],
        "players": lobby["players"]
    }, room=lobby_code)
