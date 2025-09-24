# engine.py
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store lobbies in memory
lobbies = {}
# Example:
# {
#   "ABCD": {
#       "host": "Alice",
#       "players": ["Alice", "Bob"],
#       "game_mode": "reverse_guessing",
#       "max_players": 4,
#       "max_rounds": 5,
#       "current_round": 0,
#       "game_active": False,
#       "votes": {}   # added for round management
#   }
# }


def generate_code(length=4):
    """Generate random uppercase lobby code."""
    return ''.join(random.choices(string.ascii_uppercase, k=length))


# ---------- ROUND MANAGER ----------
class RoundManager:
    def __init__(self, socketio):
        self.socketio = socketio

    def start_round(self, lobby_code):
        lobby = lobbies.get(lobby_code)
        if not lobby:
            return

        lobby["votes"] = {}
        lobby["game_active"] = True
        round_number = lobby["current_round"]

        self.socketio.emit("round_started", {
            "lobbyCode": lobby_code,
            "round": round_number,
            "maxRounds": lobby["max_rounds"]
        }, room=lobby_code)

    def submit_vote(self, lobby_code, username, choice):
        lobby = lobbies.get(lobby_code)
        if not lobby or not lobby.get("game_active"):
            return

        lobby["votes"][username] = choice

        # All players voted?
        if len(lobby["votes"]) >= len(lobby["players"]):
            self.end_round(lobby_code)

    def end_round(self, lobby_code):
        lobby = lobbies.get(lobby_code)
        if not lobby:
            return

        lobby["game_active"] = False
        round_number = lobby["current_round"]

        # Placeholder summary payload
        summary = {
            "round": round_number,
            "votes": lobby["votes"]
        }

        # Emit summary
        self.socketio.emit("round_summary", {
            "lobbyCode": lobby_code,
            "summary": summary
        }, room=lobby_code)

        # Delay, then move to next round or end game
        self.socketio.start_background_task(self._delayed_next_round, lobby_code)

    def _delayed_next_round(self, lobby_code):
        self.socketio.sleep(3)  # 3s delay
        lobby = lobbies.get(lobby_code)
        if not lobby:
            return

        if lobby["current_round"] < lobby["max_rounds"]:
            lobby["current_round"] += 1
            self.start_round(lobby_code)
        else:
            self.socketio.emit("game_over", {
                "lobbyCode": lobby_code,
                "results": "Final results placeholder"
            }, room=lobby_code)


round_manager = RoundManager(socketio)


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
        "current_round": 0,   # 0 = not started
        "game_active": False,
        "votes": {}
    }

    join_room(lobby_code)
    emit("lobby_created", {
        "username": username,
        "lobbyCode": lobby_code,
        "gameMode": game_mode,
        "maxRounds": lobbies[lobby_code]["max_rounds"]
    })


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

    emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)
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

    if lobby.get("host") == username and lobby["players"]:
        lobby["host"] = lobby["players"][0]

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

        if requested_max_rounds is not None:
            try:
                mr = int(requested_max_rounds)
                lobby["max_rounds"] = max(1, mr)
            except Exception:
                pass

        lobby["game_mode"] = mode
        lobby["game_active"] = True
        lobby["current_round"] = 1

        emit("game_started", {
            "mode": mode,
            "current_round": lobby["current_round"],
            "max_rounds": lobby["max_rounds"]
        }, room=lobby_code)

        # kick off round 1
        round_manager.start_round(lobby_code)


@socketio.on("submit_vote")
def on_submit_vote(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    choice = data.get("choice")

    round_manager.submit_vote(lobby_code, username, choice)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
