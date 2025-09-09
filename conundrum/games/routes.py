# conundrum/games/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from .. import socket as socket_module  # central lobbies live in socket.py

# Import game classes
from .reverse_guessing import ReverseGuessingGame
from .bad_advice_hotline import BadAdviceGame
from .emoji_translation import EmojiTranslationGame
from .obviously_lies import ObviouslyLiesGame

games_bp = Blueprint("games", __name__, url_prefix="/games")

# --------------------------
# Game Instances (can be linked to lobbies later)
# --------------------------
reverse_game = ReverseGuessingGame()
bad_advice_game = BadAdviceGame()
emoji_game = EmojiTranslationGame()
lies_game = ObviouslyLiesGame()

# --------------------------
# Lobby Route
# --------------------------
@games_bp.route("/lobby")
def lobby():
    """Render the lobby page with user + lobby info."""
    username = request.args.get("username")
    lobby_code = request.args.get("lobby")
    game_mode = request.args.get("mode")

    if not username or not lobby_code or not game_mode:
        return redirect(url_for("home"))

    session["username"] = username
    session["lobby"] = lobby_code
    session["mode"] = game_mode

    # Check if this user is the host
    is_host = False
    if lobby_code in socket_module.lobbies:
        if socket_module.lobbies[lobby_code].get("host") == username:
            is_host = True

    return render_template(
        "lobby.html",
        username=username,
        lobby_code=lobby_code,
        game_mode=game_mode,
        is_host=is_host
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
        return redirect(url_for("home"))

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
        # fallback → back to lobby
        return redirect(url_for("games.lobby", username=username, lobby=lobby_code, mode=game_mode))
