# engine.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
socketio = SocketIO(app)

# Store lobbies in memory
# Format: { "ABCD": {"host": "Alice", "players": ["Alice"], "game_mode": "reverse_guessing", "max_players": 4} }
lobbies = {}


def generate_code(length=4):
    """Generate random 4-letter lobby code."""
    return ''.join(random.choices(string.ascii_uppercase, k=length))


# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/games/lobby")
def lobby():
    username = request.args.get("username")
    lobby_code = request.args.get("lobby")
    mode = request.args.get("mode")

    if not username or not lobby_code or lobby_code not in lobbies:
        return "❌ Invalid lobby", 400

    is_host = (username == lobbies[lobby_code]["host"])
    return render_template("lobby.html",
                           username=username,
                           lobby_code=lobby_code,
                           game_mode=mode,
                           is_host=is_host)


# ---------- SOCKET EVENTS ----------
@socketio.on("create_lobby")
def on_create_lobby(data):
    username = data.get("username")
    max_players = int(data.get("maxPlayers", 4))
    game_mode = data.get("gameMode", "reverse_guessing")

    # generate unique code
    lobby_code = generate_code()
    while lobby_code in lobbies:
        lobby_code = generate_code()

    # create lobby
    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "game_mode": game_mode,
        "max_players": max_players
    }

    join_room(lobby_code)
    emit("lobby_created", {"username": username, "lobbyCode": lobby_code, "gameMode": game_mode})


@socketio.on("join_lobby")
def on_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode", "").upper()

    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby does not exist"})
        return

    lobby = lobbies[lobby_code]
    if username in lobby["players"]:
        emit("error_message", {"message": "You are already in this lobby"})
        return
    if len(lobby["players"]) >= lobby["max_players"]:
        emit("error_message", {"message": "Lobby is full"})
        return

    lobby["players"].append(username)
    join_room(lobby_code)

    # update everyone in room
    emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)
    # tell joining player to go to lobby page
    emit("lobby_joined", {"username": username, "lobbyCode": lobby_code, "gameMode": lobby["game_mode"]})


@socketio.on("send_message")
def on_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    msg = data.get("message")

    if lobby_code in lobbies:
        emit("receive_message", {"username": username, "message": msg}, room=lobby_code)


@socketio.on("start_game")
def on_start_game(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    mode = data.get("mode")

    if lobby_code in lobbies and lobbies[lobby_code]["host"] == username:
        emit("game_started", {"mode": mode}, room=lobby_code)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
