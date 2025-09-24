# engine.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store lobbies in memory
# Format:
# {
#   "ABCD": {
#       "host": "Alice",
#       "players": ["Alice", "Bob"],
#       "game_mode": "reverse_guessing",
#       "max_players": 4,
#       "max_rounds": 5,
#       "current_round": 0,
#       "game_active": False
#   }
# }
lobbies = {}


def generate_code(length=4):
    """Generate random uppercase lobby code."""
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
    return render_template(
        "lobby.html",
        username=username,
        lobby_code=lobby_code,
        game_mode=mode,
        is_host=is_host,
        lobby_data=lobbies[lobby_code]
    )


# ---------- SOCKET EVENTS ----------
@socketio.on("create_lobby")
def on_create_lobby(data):
    username = data.get("username")
    max_players = int(data.get("maxPlayers", 4))
    max_rounds = int(data.get("maxRounds", 5))
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
        "max_players": max_players,
        "max_rounds": max(1, max_rounds),
        "current_round": 0,   # 0 = not started, will set to 1 on start
        "game_active": False
    }

    join_room(lobby_code)
    emit(
        "lobby_created",
        {
            "username": username,
            "lobbyCode": lobby_code,
            "gameMode": game_mode,
            "maxRounds": lobbies[lobby_code]["max_rounds"]
        },
    )


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


@socketio.on("leave_lobby")
def on_leave_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode", "").upper()

    if lobby_code not in lobbies:
        return

    lobby = lobbies[lobby_code]
    if username in lobby["players"]:
        lobby["players"].remove(username)
        leave_room(lobby_code)

    # if host left, pick a new host (simple fallback)
    if lobby.get("host") == username and lobby["players"]:
        lobby["host"] = lobby["players"][0]

    # if no players left, remove lobby
    if not lobby["players"]:
        del lobbies[lobby_code]
        return

    emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)


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
    requested_max_rounds = data.get("maxRounds")

    if lobby_code in lobbies and lobbies[lobby_code]["host"] == username:
        lobby = lobbies[lobby_code]
        # allow host to override max rounds on start if provided
        if requested_max_rounds is not None:
            try:
                mr = int(requested_max_rounds)
                lobby["max_rounds"] = max(1, mr)
            except Exception:
                pass

        lobby["game_mode"] = mode
        lobby["game_active"] = True
        lobby["current_round"] = 1  # start at round 1

        emit(
            "game_started",
            {
                "mode": mode,
                "current_round": lobby["current_round"],
                "max_rounds": lobby["max_rounds"]
            },
            room=lobby_code
        )


@socketio.on("next_round")
def on_next_round(data):
    """Host triggers advancing to the next round."""
    lobby_code = data.get("lobbyCode")
    username = data.get("username")

    if lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found"})
        return

    lobby = lobbies[lobby_code]
    if lobby.get("host") != username:
        emit("error_message", {"message": "Only the host can advance rounds"})
        return

    if not lobby.get("game_active"):
        emit("error_message", {"message": "Game is not active"})
        return

    # advance round
    if lobby["current_round"] >= lobby["max_rounds"]:
        # game over
        lobby["game_active"] = False
        emit("game_over", {"final_round": lobby["current_round"]}, room=lobby_code)
        return

    lobby["current_round"] += 1
    emit(
        "round_updated",
        {"current_round": lobby["current_round"], "max_rounds": lobby["max_rounds"]},
        room=lobby_code
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
