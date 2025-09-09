# conundrum/games/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from .. import socket as socket_module  # central lobbies live in socket.py

# Import game classes
from .reverse_guessing import ReverseGuessingGame
from .bad_advice_hotline import BadAdviceGame
from .emoji_translation import EmojiTranslationGame
from .obviously_lies import ObviouslyLiesGame

games_bp = Blueprint("games", __name__, url_prefix="/games")

# Game instances (you can later attach them to lobbies when starting a game)
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

    # Check if this user is the host (from socket.py lobbies)
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
