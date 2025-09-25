from flask_socketio import emit, join_room
from flask import request
from . import socketio
import random
import string
from conundrum.games.obviously_lies import ObviouslyLiesGame
from conundrum.games.reverse_guessing import ReverseGuessingGame
from conundrum.games.bad_advice_hotline import BadAdviceHotlineGame
from conundrum.games.emoji_translation import EmojiTranslationGame
from conundrum.utils.profanity_filter import ProfanityFilter
from conundrum.utils.round_manager import round_manager


# Lobby state: lobby_code -> lobby data
lobbies = {}


# Game manager instances
obviously_lies_game_manager = ObviouslyLiesGame()
reverse_guessing_game_manager = ReverseGuessingGame()
bad_advice_hotline_game_manager = BadAdviceHotlineGame()
emoji_translation_game_manager = EmojiTranslationGame()


# Track votes per lobby: { lobby_code: { player: choice, ... }, ... }
lobby_votes = {}


# Global profanity filter (load from JSON if exists)
pf = ProfanityFilter.from_json("data/profanity.json")


def generate_lobby_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


# --- Lobby management ---


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
        "game_mode": None,
    }

    max_rounds = int(data.get("maxRounds", 3))  # default 3 rounds

    round_manager.register_lobby(lobby_code, max_rounds=max_rounds)

    join_room(lobby_code)

    emit("lobby_created", {"lobbyCode": lobby_code, "username": username, "maxPlayers": max_players}, room=request.sid)
    emit("lobby_update", {"host": username, "players": lobbies[lobby_code]["players"]}, room=lobby_code)


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

    emit(
        "lobby_joined",
        {
            "lobbyCode": lobby_code,
            "username": username,
            "gameMode": lobby["game_mode"],
            "players": lobby["players"],
        },
        room=request.sid,
    )

    emit("lobby_update", {"host": lobby["host"], "players": lobby["players"]}, room=lobby_code)


@socketio.on("send_message")
def handle_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    message = data.get("message")

    if not lobby_code or lobby_code not in lobbies or not message:
        emit("error_message", {"message": "Invalid message."}, room=request.sid)
        return

    censored, violations = pf.clean(message)

    emit("receive_message", {"username": username, "message": censored, "violations": violations}, room=lobby_code)


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

    lobby["game_mode"] = mode

    round_manager.start_game(lobby_code)
    round_manager.start_round(lobby_code)

    lobby_votes[lobby_code] = {}

    # Setup round handler callbacks based on mode
    if mode == "obviously_lies":
        obviously_lies_game_manager.end_round(lobby_code)
        round_manager.set_handler(
            lobby_code,
            {
                "on_round_end": lambda lc, rn: obviously_lies_game_manager.end_round(lc),
                "reset_round": lambda lc: obviously_lies_game_manager.reset_round_state(lc),
            },
        )

    elif mode == "reverse_guessing":
        reverse_guessing_game_manager.end_round(lobby_code)
        round_manager.set_handler(
            lobby_code,
            {
                "on_round_end": lambda lc, rn: reverse_guessing_game_manager.end_round(lc),
                "reset_round": lambda lc: reverse_guessing_game_manager.reset_round_state(lc),
            },
        )

    elif mode == "bad_advice_hotline":
        bad_advice_hotline_game_manager.end_round(lobby_code)
        round_manager.set_handler(
            lobby_code,
            {
                "on_round_end": lambda lc, rn: bad_advice_hotline_game_manager.end_round(lc),
                "reset_round": lambda lc: bad_advice_hotline_game_manager.reset_round_state(lc),
            },
        )

    elif mode == "emoji_translation":
        emoji_translation_game_manager.end_round(lobby_code)
        round_manager.set_handler(
            lobby_code,
            {
                "on_round_end": lambda lc, rn: emoji_translation_game_manager.end_round(lc),
                "reset_round": lambda lc: emoji_translation_game_manager.reset_round_state(lc),
            },
        )

    emit("game_started", {"lobbyCode": lobby_code, "mode": mode}, room=lobby_code)


# --- Bad Advice Hotline Handlers ---


@socketio.on("bad_advice_hotline_start_round")
def bad_advice_hotline_start_round(data):
    lobby_code = data.get("lobbyCode")
    question = data.get("question")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return
    if not question:
        emit("error_message", {"message": "Question is required."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    bad_advice_hotline_game_manager.start_round(lobby_code, question, players, host)

    lobby_votes[lobby_code] = {}

    emit("bad_advice_hotline_round_started", {"question": question}, room=lobby_code)
    emit("bad_advice_hotline_all_answers", {"answers": []}, room=lobby_code)


@socketio.on("bad_advice_hotline_submit_bad_advice")
def bad_advice_hotline_submit_bad_advice(data):
    lobby_code = data.get("lobbyCode")
    player = data.get("player")
    bad_advice = data.get("badAdvice")

    if not lobby_code or bad_advice is None or not bad_advice_hotline_game_manager.games.get(lobby_code):
        emit("error_message", {"message": "Round not found or bad advice missing."}, room=request.sid)
        return

    censored, violations = pf.clean(bad_advice)

    success = bad_advice_hotline_game_manager.submit_bad_advice(lobby_code, player, censored)
    if not success:
        emit("error_message", {"message": "Failed to submit bad advice."}, room=request.sid)
        return

    emit("bad_advice_hotline_bad_advice_submitted", {"badAdvice": censored, "violations": violations}, room=lobby_code)

    player_answers = bad_advice_hotline_game_manager.get_submitted_bad_advice(lobby_code)
    emit("player_own_answers", {"answers": [ans for p, ans in player_answers.items() if p == player]}, room=request.sid)

    if bad_advice_hotline_game_manager.all_bad_advice_submitted(lobby_code):
        all_answers = bad_advice_hotline_game_manager.get_all_bad_advice_answers(lobby_code)
        random.shuffle(all_answers)
        emit("bad_advice_hotline_all_answers", {"answers": all_answers}, room=lobby_code)


@socketio.on("bad_advice_hotline_vote")
def bad_advice_hotline_vote(data):
    lobby_code = data.get("lobbyCode")
    player = data.get("player")
    answer = data.get("answer")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return
    if not bad_advice_hotline_game_manager.games.get(lobby_code):
        emit("error_message", {"message": "Round not started."}, room=request.sid)
        return

    current_votes = lobby_votes.setdefault(lobby_code, {})
    if player in current_votes:
        emit("error_message", {"message": "Vote failed or already voted."}, room=request.sid)
        return
    if player == lobbies[lobby_code]["host"]:
        emit("error_message", {"message": "Host cannot vote."}, room=request.sid)
        return

    success = bad_advice_hotline_game_manager.cast_vote(lobby_code, player, answer)
    if success:
        current_votes[player] = answer
        emit("vote_confirmed", {"answer": answer, "player": player}, room=request.sid)
        emit("update_votes", {"votes": current_votes}, room=lobby_code)
        scores = bad_advice_hotline_game_manager.get_scores(lobby_code)
        emit("update_scores", {"scores": scores}, room=lobby_code)
    else:
        emit("error_message", {"message": "Vote failed or already voted."}, room=request.sid)


from flask_socketio import emit, join_room, leave_room
from flask import request
from . import socketio
import random
import string
from conundrum.games.obviously_lies import ObviouslyLiesGame
from conundrum.games.reverse_guessing import ReverseGuessingGame
from conundrum.games.bad_advice_hotline import BadAdviceHotlineGame
from conundrum.games.emoji_translation import EmojiTranslationGame
from conundrum.utils.profanity_filter import ProfanityFilter
from conundrum.utils.round_manager import round_manager


# Lobby state: lobby_code -> lobby data
lobbies = {}

# Game manager instances
obviously_lies_game_manager = ObviouslyLiesGame()
reverse_guessing_game_manager = ReverseGuessingGame()
bad_advice_hotline_game_manager = BadAdviceHotlineGame()
emoji_translation_game_manager = EmojiTranslationGame()

# Track votes per lobby
lobby_votes = {}

# Global profanity filter
pf = ProfanityFilter.from_json("data/profanity.json")


def generate_lobby_code():
    """Generates a random 4-character lobby code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


# --- Lobby Management --- 

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    max_players = data.get("maxPlayers", 8)

    if not username:
        emit("error_message", {"message": "Username is required."}, room=request.sid)
        return

    lobby_code = generate_lobby_code()
    while lobby_code in lobbies:
        lobby_code = generate_lobby_code()

    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "max_players": max_players,
        "game_mode": None,
        "current_round": 0,
        "game_active": False
    }

    max_rounds = data.get("maxRounds", 3)
    round_manager.register_lobby(lobby_code, max_rounds)

    join_room(lobby_code)

    emit("lobby_created", {"lobbyCode": lobby_code, "username": username, "maxPlayers": max_players}, room=request.sid)
    emit("lobby_update", {"host": username, "players": lobbies[lobby_code]["players"]}, room=lobby_code)


@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if not username or not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Invalid join request."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if username in lobby["players"]:
        emit("error_message", {"message": "You are already in this lobby."}, room=request.sid)
        return
    if len(lobby["players"]) >= lobby["max_players"]:
        emit("error_message", {"message": "Lobby is full."}, room=request.sid)
        return

    lobby["players"].append(username)
    join_room(lobby_code)

    emit("lobby_joined", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": lobby["game_mode"],
        "players": lobby["players"]
    }, room=request.sid)

    emit("lobby_update", {"host": lobby["host"], "players": lobby["players"]}, room=lobby_code)


@socketio.on("send_message")
def handle_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    message = data.get("message")

    if not message or lobby_code not in lobbies:
        emit("error_message", {"message": "Invalid message or lobby."}, room=request.sid)
        return

    censored, violations = pf.clean(message)

    emit("receive_message", {"username": username, "message": censored, "violations": violations}, room=lobby_code)


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
        emit("error_message", {"message": "Only the host can start the game."}, room=request.sid)
        return

    if not mode:
        emit("error_message", {"message": "Game mode is required to start."}, room=request.sid)
        return

    lobby["game_mode"] = mode
    lobby["game_active"] = True
    lobby["current_round"] = 1

    round_manager.start_game(lobby_code)
    round_manager.start_round(lobby_code)

    emit("game_started", {
        "lobbyCode": lobby_code,
        "mode": mode,
        "current_round": lobby["current_round"]
    }, room=lobby_code)


@socketio.on("next_round")
def handle_next_round(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")

    if lobby_code not in lobbies or lobbies[lobby_code]["host"] != username:
        emit("error_message", {"message": "Only the host can advance to the next round."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if not lobby["game_active"]:
        emit("error_message", {"message": "Game is not active."}, room=request.sid)
        return

    if lobby["current_round"] >= lobby["max_rounds"]:
        emit("game_over", {"message": "Game Over. All rounds are complete."}, room=lobby_code)
        lobby["game_active"] = False
        return

    lobby["current_round"] += 1
    emit("round_updated", {"current_round": lobby["current_round"], "max_rounds": lobby["max_rounds"]}, room=lobby_code)


# --- Game Mode Handlers --- 

@socketio.on("bad_advice_hotline_start_round")
def handle_bad_advice_hotline_start_round(data):
    lobby_code = data.get("lobbyCode")
    question = data.get("question")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not question:
        emit("error_message", {"message": "Lobby not found or invalid question."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    bad_advice_hotline_game_manager.start_round(lobby_code, question, players, host)
    emit("bad_advice_hotline_round_started", {"question": question}, room=lobby_code)
    emit("bad_advice_hotline_all_answers", {"answers": []}, room=lobby_code)


@socketio.on("obviously_lies_start_round")
def handle_obviously_lies_start_round(data):
    lobby_code = data.get("lobbyCode")
    question = data.get("question")
    correct_answer = data.get("correctAnswer")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not question or not correct_answer:
        emit("error_message", {"message": "Lobby not found, question or correct answer missing."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    obviously_lies_game_manager.start_round(lobby_code, question, correct_answer, players, host)
    emit("obviously_lies_round_started", {"question": question}, room=lobby_code)
    emit("obviously_lies_all_answers", {"answers": [correct_answer]}, room=lobby_code)


@socketio.on("emoji_translation_start_round")
def handle_emoji_translation_start_round(data):
    lobby_code = data.get("lobbyCode")
    emoji_prompt = data.get("emojiPrompt")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not emoji_prompt:
        emit("error_message", {"message": "Lobby not found or emoji prompt missing."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    emoji_translation_game_manager.start_round(lobby_code, emoji_prompt, players, host)
    emit("emoji_translation_round_started", {"emoji_prompt": emoji_prompt}, room=lobby_code)
    emit("emoji_translation_all_guesses", {"guesses": []}, room=lobby_code)


# --- Helper Method for Voting --- 

@socketio.on("vote")
def handle_vote(data):
    lobby_code = data.get("lobbyCode")
    player = data.get("player")
    answer = data.get("answer")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if player == lobby["host"]:
        emit("error_message", {"message": "Host cannot vote."}, room=request.sid)
        return

    if not answer:
        emit("error_message", {"message": "Answer required."}, room=request.sid)
        return

    current_votes = lobby_votes.setdefault(lobby_code, {})
    if player in current_votes:
        emit("error_message", {"message": "You already voted."}, room=request.sid)
        return

    success = bad_advice_hotline_game_manager.cast_vote(lobby_code, player, answer)
    if success:
        current_votes[player] = answer
        emit("vote_confirmed", {"answer": answer, "player": player}, room=lobby_code)
        scores = bad_advice_hotline_game_manager.get_scores(lobby_code)
        emit("update_scores", {"scores": scores}, room=lobby_code)
    else:
        emit("error_message", {"message": "Vote failed."}, room=request.sid)

from flask_socketio import emit, join_room, leave_room
from flask import request
from . import socketio
import random
import string
from conundrum.games.obviously_lies import ObviouslyLiesGame
from conundrum.games.reverse_guessing import ReverseGuessingGame
from conundrum.games.bad_advice_hotline import BadAdviceHotlineGame
from conundrum.games.emoji_translation import EmojiTranslationGame
from conundrum.utils.profanity_filter import ProfanityFilter
from conundrum.utils.round_manager import round_manager

# Lobby state: lobby_code -> lobby data
lobbies = {}

# Game manager instances
obviously_lies_game_manager = ObviouslyLiesGame()
reverse_guessing_game_manager = ReverseGuessingGame()
bad_advice_hotline_game_manager = BadAdviceHotlineGame()
emoji_translation_game_manager = EmojiTranslationGame()

# Track votes per lobby
lobby_votes = {}

# Global profanity filter
pf = ProfanityFilter.from_json("data/profanity.json")

def generate_lobby_code():
    """Generates a random 4-character lobby code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

# --- Lobby Management --- 

@socketio.on("create_lobby")
def handle_create_lobby(data):
    username = data.get("username")
    max_players = data.get("maxPlayers", 8)

    if not username:
        emit("error_message", {"message": "Username is required."}, room=request.sid)
        return

    lobby_code = generate_lobby_code()
    while lobby_code in lobbies:
        lobby_code = generate_lobby_code()

    lobbies[lobby_code] = {
        "host": username,
        "players": [username],
        "max_players": max_players,
        "game_mode": None,
        "current_round": 0,
        "game_active": False
    }

    max_rounds = data.get("maxRounds", 3)
    round_manager.register_lobby(lobby_code, max_rounds)

    join_room(lobby_code)

    emit("lobby_created", {"lobbyCode": lobby_code, "username": username, "maxPlayers": max_players}, room=request.sid)
    emit("lobby_update", {"host": username, "players": lobbies[lobby_code]["players"]}, room=lobby_code)


@socketio.on("join_lobby")
def handle_join_lobby(data):
    username = data.get("username")
    lobby_code = data.get("lobbyCode")

    if not username or not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Invalid join request."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if username in lobby["players"]:
        emit("error_message", {"message": "You are already in this lobby."}, room=request.sid)
        return
    if len(lobby["players"]) >= lobby["max_players"]:
        emit("error_message", {"message": "Lobby is full."}, room=request.sid)
        return

    lobby["players"].append(username)
    join_room(lobby_code)

    emit("lobby_joined", {
        "lobbyCode": lobby_code,
        "username": username,
        "gameMode": lobby["game_mode"],
        "players": lobby["players"]
    }, room=request.sid)

    emit("lobby_update", {"host": lobby["host"], "players": lobby["players"]}, room=lobby_code)


@socketio.on("send_message")
def handle_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    message = data.get("message")

    if not message or lobby_code not in lobbies:
        emit("error_message", {"message": "Invalid message or lobby."}, room=request.sid)
        return

    censored, violations = pf.clean(message)

    emit("receive_message", {"username": username, "message": censored, "violations": violations}, room=lobby_code)


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
        emit("error_message", {"message": "Only the host can start the game."}, room=request.sid)
        return

    if not mode:
        emit("error_message", {"message": "Game mode is required to start."}, room=request.sid)
        return

    lobby["game_mode"] = mode
    lobby["game_active"] = True
    lobby["current_round"] = 1

    round_manager.start_game(lobby_code)
    round_manager.start_round(lobby_code)

    emit("game_started", {
        "lobbyCode": lobby_code,
        "mode": mode,
        "current_round": lobby["current_round"]
    }, room=lobby_code)


@socketio.on("next_round")
def handle_next_round(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")

    if lobby_code not in lobbies or lobbies[lobby_code]["host"] != username:
        emit("error_message", {"message": "Only the host can advance to the next round."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if not lobby["game_active"]:
        emit("error_message", {"message": "Game is not active."}, room=request.sid)
        return

    if lobby["current_round"] >= lobby["max_rounds"]:
        emit("game_over", {"message": "Game Over. All rounds are complete."}, room=lobby_code)
        lobby["game_active"] = False
        return

    lobby["current_round"] += 1
    emit("round_updated", {"current_round": lobby["current_round"], "max_rounds": lobby["max_rounds"]}, room=lobby_code)


# --- Game Mode Handlers --- 

@socketio.on("obviously_lies_start_round")
def handle_obviously_lies_start_round(data):
    lobby_code = data.get("lobbyCode")
    question = data.get("question")
    correct_answer = data.get("correctAnswer")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not question or not correct_answer:
        emit("error_message", {"message": "Lobby not found, question or correct answer missing."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    obviously_lies_game_manager.start_round(lobby_code, question, correct_answer, players, host)
    emit("obviously_lies_round_started", {"question": question}, room=lobby_code)
    emit("obviously_lies_all_answers", {"answers": [correct_answer]}, room=lobby_code)


@socketio.on("reverse_guessing_start_round")
def handle_reverse_guessing_start_round(data):
    lobby_code = data.get("lobbyCode")
    answer = data.get("answer")
    correct_question = data.get("correctQuestion")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not answer or not correct_question:
        emit("error_message", {"message": "Answer or correct question missing."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    reverse_guessing_game_manager.start_round(lobby_code, answer, correct_question, players, host)
    emit("reverse_guessing_round_started", {"answer": answer}, room=lobby_code)
    emit("reverse_guessing_all_questions", {"questions": [correct_question]}, room=lobby_code)


@socketio.on("emoji_translation_start_round")
def handle_emoji_translation_start_round(data):
    lobby_code = data.get("lobbyCode")
    emoji_prompt = data.get("emojiPrompt")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies or not emoji_prompt:
        emit("error_message", {"message": "Emoji prompt is required."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]

    emoji_translation_game_manager.start_round(lobby_code, emoji_prompt, players, host)
    emit("emoji_translation_round_started", {"emoji_prompt": emoji_prompt}, room=lobby_code)
    emit("emoji_translation_all_guesses", {"guesses": []}, room=lobby_code)
