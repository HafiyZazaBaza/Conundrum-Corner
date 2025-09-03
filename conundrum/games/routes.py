from flask import Blueprint, render_template, session, redirect, url_for
from .. import socketio
from flask_socketio import join_room, emit

# Import game classes
from .reverse_guessing import ReverseGuessingGame
from .bad_advice_hotline import BadAdviceGame
from .emoji_translation import EmojiTranslationGame
from .obviously_lies import ObviouslyLiesGame

games_bp = Blueprint("games", __name__, url_prefix="/games")

# Create game 
reverse_game = ReverseGuessingGame()
bad_advice_game = BadAdviceGame()
emoji_game = EmojiTranslationGame()
lies_game = ObviouslyLiesGame()

# Track connected players ( sid: username )
players = {}

# --------------------------
# Lobby Route
# --------------------------

@games_bp.route("/lobby")
def lobby():
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))
    return render_template("lobby.html", username=username)

# --------------------------
# Lobby Events
# --------------------------

@socketio.on("join_room")
def handle_join(data):
    username = session.get("username")
    room = data.get("room")
    if username and room:
        players[session.sid] = username
        join_room(room)
        emit("user_joined", {"username": username}, room=room)

@socketio.on("send_message")
def handle_message(data):
    username = session.get("username")
    room = data.get("room")
    message = data.get("message")
    if username and room and message:
        emit("receive_message", {"username": username, "message": message}, room=room)

# --------------------------
# Reverse Guessing Game
# --------------------------

@socketio.on("reverse_start_round")
def reverse_start_round(data):
    room = data.get("room")
    reverse_game.start_round(socketio, room, players)

@socketio.on("reverse_submit_question")
def reverse_submit_question(data):
    sid = session.sid
    username = session.get("username")
    room = data.get("room")
    question = data.get("question")
    reverse_game.submit_question(socketio, room, sid, username, question)

@socketio.on("reverse_guess_answer")
def reverse_guess_answer(data):
    username = session.get("username")
    room = data.get("room")
    guess = data.get("guess")
    reverse_game.guess_answer(socketio, room, username, guess, players)

# --------------------------
# Bad Advice Hotline
# --------------------------

@socketio.on("badadvice_start_round")
def badadvice_start_round(data):
    room = data.get("room")
    bad_advice_game.start_round(socketio, room, players)

@socketio.on("badadvice_submit_answer")
def badadvice_submit_answer(data):
    sid = session.sid
    room = data.get("room")
    answer = data.get("answer")
    bad_advice_game.submit_answer(socketio, room, sid, answer)

@socketio.on("badadvice_cast_vote")
def badadvice_cast_vote(data):
    sid = session.sid
    room = data.get("room")
    voted_sid = data.get("voted_sid")
    bad_advice_game.cast_vote(socketio, room, sid, voted_sid, players)

# --------------------------
# Emoji Translation
# --------------------------

@socketio.on("emoji_start_round")
def emoji_start_round(data):
    room = data.get("room")
    emoji_game.start_round(socketio, room, players)

@socketio.on("emoji_submit_translation")
def emoji_submit_translation(data):
    sid = session.sid
    room = data.get("room")
    emoji_string = data.get("emoji")
    emoji_game.submit_translation(socketio, room, sid, emoji_string)

@socketio.on("emoji_submit_guess")
def emoji_submit_guess(data):
    sid = session.sid
    room = data.get("room")
    guess = data.get("guess")
    username = session.get("username")
    emoji_game.submit_guess(socketio, room, sid, guess, username)

# --------------------------
# Obviously Lies
# --------------------------

@socketio.on("lies_set_question")
def lies_set_question(data):
    room = data.get("room")
    question = data.get("question")
    correct_answer = data.get("correct_answer")
    host = session.get("username")
    lies_game.set_question(socketio, room, question, correct_answer, host)

@socketio.on("lies_submit_fake")
def lies_submit_fake(data):
    sid = session.sid
    room = data.get("room")
    fake_answer = data.get("answer")
    lies_game.submit_fake_answer(socketio, room, sid, fake_answer)

@socketio.on("lies_start_voting")
def lies_start_voting(data):
    room = data.get("room")
    lies_game.start_voting(socketio, room)

@socketio.on("lies_cast_vote")
def lies_cast_vote(data):
    sid = session.sid
    room = data.get("room")
    chosen_answer = data.get("chosen_answer")
    username = session.get("username")
    lies_game.cast_vote(socketio, room, sid, chosen_answer, username)

@socketio.on("lies_end_round")
def lies_end_round(data):
    room = data.get("room")
    lies_game.end_round(socketio, room)
