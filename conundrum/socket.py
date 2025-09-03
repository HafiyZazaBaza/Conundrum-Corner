from flask import session
from flask_socketio import join_room, leave_room, emit
from . import socketio
import random, string

# Stores lobbies in memory (key = lobbyCode, value = dict)
lobbies = {}
# Stores sid -> lobbyCode mapping
user_rooms = {}

def generate_lobby_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    max_players = int(data.get("maxPlayers", 4))
    game_mode = data.get("gameMode")

    # generate unique lobby code
    lobby_code = generate_lobby_code()
    while lobby_code in lobbies:
        lobby_code = generate_lobby_code()

    # create lobby
    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "max_players": max_players,
        "game_mode": game_mode
    }

    # save mapping
    user_rooms[session.sid] = lobby_code
    join_room(lobby_code)

    emit("lobby_created", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": game_mode
    }, room=session.sid)

@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=session.sid)
        return

    lobby = lobbies[lobby_code]
    if len(lobby["players"]) >= lobby["max_players"]:
        emit("error_message", {"message": "Lobby is full."}, room=session.sid)
        return

    lobby["players"].append(username)
    user_rooms[session.sid] = lobby_code
    join_room(lobby_code)

    # notify the joining user
    emit("lobby_joined", {"username": username, "lobbyCode": lobby_code}, room=session.sid)
    # notify everyone in the lobby
    emit("lobby_update", {"players": lobby["players"]}, room=lobby_code)

@socketio.on("disconnect")
def handle_disconnect():
    sid = session.sid
    if sid in user_rooms:
        lobby_code = user_rooms.pop(sid)
        lobby = lobbies.get(lobby_code)
        if lobby:
            # remove player
            for p in lobby["players"]:
                if p == lobby["host"]:
                    continue
            # if empty, delete lobby
            if len(lobby["players"]) == 0:
                del lobbies[lobby_code]
            else:
                emit("lobby_update", {"players": lobby["players"]}, room=lobby_code)
