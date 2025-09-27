# conundrum/games/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from conundrum import socket as socket_module  

# Import game classes
from conundrum.games.obviously_lies import ObviouslyLiesGame
from conundrum.utils.profanity_filter import ProfanityFilter

# Import main routes blueprint for redirects
from conundrum.routes import routes  
from conundrum.utils.rounds import round_manager
from engine import lobbies

# Blueprint
games_bp = Blueprint("games", __name__, url_prefix="/games")

# Game Instances
lies_game = ObviouslyLiesGame()

# Profanity Filter Instance
pf = ProfanityFilter()

# Lobby Route
@games_bp.route("/lobby")
def lobby():
    """Render the lobby page with user + lobby info."""
    username = request.args.get("username")
    lobby_code = request.args.get("lobby")

    if not username or not lobby_code:
        return redirect(url_for("routes.home"))  # routes.home is in main routes.py

    session["username"] = username
    session["lobby"] = lobby_code

    # Lobby data defaults
    is_host = False
    game_mode = None
    lobby_data = {}

    if lobby_code in socket_module.lobbies:
        lobby = socket_module.lobbies[lobby_code]
        if lobby.get("host") == username:
            is_host = True
        game_mode = lobby.get("game_mode")  # may be None until host selects
        lobby_data = {
            "max_rounds": lobby.get("max_rounds"),
            "current_round": lobby.get("current_round"),
            "game_active": lobby.get("game_active"),
        }

    return render_template(
        "lobby.html",
        username=username,
        lobby_code=lobby_code,
        game_mode=game_mode,
        is_host=is_host,
        lobby_data=lobby_data,
    )

# --------------------------
# Play Route
# --------------------------
@games_bp.route("/play")
def play():
    """Render the correct game page depending on mode."""
    username = request.args.get("username")
    lobby_code = request.args.get("lobby")
    game_mode = request.args.get("mode")

    if not username or not lobby_code or not game_mode:
        return redirect(url_for("routes.home"))

    # Save session info
    session["username"] = username
    session["lobby"] = lobby_code
    session["mode"] = game_mode

    # Whitelist valid modes → maps directly to template files
    valid_modes = {
        "reverse_guessing": "reverse_guessing.html",
        "bad_advice_hotline": "bad_advice_hotline.html",
        "emoji_translation": "emoji_translation.html",
        "obviously_lies": "obviously_lies.html",
    }

    if game_mode in valid_modes:
        return render_template(valid_modes[game_mode], username=username, lobby_code=lobby_code)
    else:
        return redirect(url_for("games.lobby", username=username, lobby=lobby_code))

# --------------------------
# Profanity Check API
# --------------------------
@games_bp.route("/check_message", methods=["POST"])
def check_message():
    """API endpoint to check + censor a message with the profanity filter."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    violations = pf.check(message)
    censored = pf.censor(message)

    return jsonify({
        "original": message,
        "censored": censored,
        "violations": violations,
    })

@routes.route("/create_lobby", methods=["POST"])
def create_lobby():
    data = request.get_json()
    lobby_id = data.get("lobby_id")
    host = data.get("username")
    max_players = data.get("max_players", 4)
    total_rounds = data.get("total_rounds", 5)  # 👈 new field

    # Create the lobby
    lobbies[lobby_id] = {
        "host": host,
        "players": [host],
        "max_players": max_players,
        "game_mode": None,
        "current_round": 1,
        "total_rounds": total_rounds,
        "game_active": False,
    }

    # Setup round manager 👇
    round_manager.setup_lobby(lobby_id, total_rounds=total_rounds)

    return jsonify({"success": True, "lobby_id": lobby_id})

# --------------------------
# Recap page
# --------------------------
@games_bp.route("/recap")
def recap():
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))
    return render_template("recap.html", username=username)

from flask import jsonify

@games_bp.route("/recap_data")
def recap_data():
    summary = session.get("recap_summary", {})
    return jsonify(summary)
