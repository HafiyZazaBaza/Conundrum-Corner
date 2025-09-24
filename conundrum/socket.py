from flask_socketio import emit, join_room
from flask import request
from . import socketio
import time
import threading
import random
import string
from conundrum.games.obviously_lies import ObviouslyLiesGame
from conundrum.utils.profanity_filter import ProfanityFilter
from conundrum.utils.round_manager import round_manager

# Lobby state: lobby_code -> lobby data
lobbies = {}

# Obviously Lies game manager instance
obviously_lies_game_manager = ObviouslyLiesGame()

# Track votes per lobby: { lobby_code: { player: answer, ... }, ... }
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

    max_rounds = int(data.get("maxRounds", 3))   # default 3 rounds if client didn't send
    round_manager.register_lobby(lobby_code, max_rounds=max_rounds)

    round_manager.set_handler(lobby_code, {
        "on_round_start": lambda lc, rn: None,  # optional: you may start game rounds yourself
        "on_round_end": lambda lc, rn: obviously_lies_game_manager.on_round_end(lc, rn),  # optional
        "reset_round": lambda lc: obviously_lies_game_manager.reset_round_state(lc),
    })

    round_manager.register_lobby(lobby_code, max_rounds=max_rounds)
    round_manager.set_handler(lobby_code, {
        "on_round_end": lambda lc, rn: obviously_lies_game_manager.end_round(lc),
        "reset_round": lambda lc: obviously_lies_game_manager.reset_round_state(lc),
    })

    join_room(lobby_code)

    emit(
        "lobby_created",
        {"lobbyCode": lobby_code, "username": username, "maxPlayers": max_players},
        room=request.sid,
    )

    emit(
        "lobby_update",
        {"host": username, "players": lobbies[lobby_code]["players"]},
        room=lobby_code,
    )


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

    emit(
        "lobby_update",
        {"host": lobby["host"], "players": lobby["players"]},
        room=lobby_code,
    )


@socketio.on("send_message")
def handle_send_message(data):
    lobby_code = data.get("lobbyCode")
    username = data.get("username")
    message = data.get("message")

    if not lobby_code or lobby_code not in lobbies or not message:
        emit("error_message", {"message": "Invalid message."}, room=request.sid)
        return

    # Run message through profanity filter
    censored, violations = pf.clean(message)

    emit(
        "receive_message",
        {"username": username, "message": censored, "violations": violations},
        room=lobby_code,
    )


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


    if mode == "obviously_lies":
        obviously_lies_game_manager.end_round(lobby_code)  # Clear existing if any
        lobby_votes[lobby_code] = {}  # Reset votes when game starts

    emit("game_started", {"lobbyCode": lobby_code, "mode": mode}, room=lobby_code)


# --- Obviously Lies game handlers ---


@socketio.on("obviously_lies_start_round")
def obviously_lies_start_round(data):
    lobby_code = data.get("lobbyCode")
    question = data.get("question")
    correct_answer = data.get("correctAnswer")
    username = data.get("username")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return
    if not question or not correct_answer:
        emit("error_message", {"message": "Question and answer required."}, room=request.sid)
        return

    lobby = lobbies[lobby_code]
    if lobby["host"] != username:
        emit("error_message", {"message": "Only the host can start the round."}, room=request.sid)
        return

    players = set(lobby["players"])
    host = lobby["host"]
    obviously_lies_game_manager.start_round(
        lobby_code, question, correct_answer, players, host
    )

    # Reset votes for new round
    lobby_votes[lobby_code] = {}

    # Broadcast question to all players (without correct answer)
    emit("obviously_lies_round_started", {"question": question}, room=lobby_code)

    # Immediately emit the correct answer as part of the anonymous answers list
    emit("obviously_lies_all_answers", {"answers": [correct_answer]}, room=lobby_code)


@socketio.on("obviously_lies_submit_false_answer")
def obviously_lies_submit_false_answer(data):
    lobby_code = data.get("lobbyCode")
    player = data.get("player")
    false_answer = data.get("falseAnswer")

    if not lobby_code or not obviously_lies_game_manager.games.get(lobby_code):
        emit("error_message", {"message": "Round not found."}, room=request.sid)
        return

    # Run through profanity filter
    censored, violations = pf.clean(false_answer)

    success = obviously_lies_game_manager.submit_false_answer(lobby_code, player, censored)
    if not success:
        emit("error_message", {"message": "Failed to submit false answer."}, room=request.sid)
        return

    emit(
        "obviously_lies_false_answer_submitted",
        {"falseAnswer": censored, "violations": violations},
        room=lobby_code,
    )

    player_answers = obviously_lies_game_manager.get_submitted_false_answers(lobby_code)
    emit(
        "player_own_answers",
        {"answers": [answer for p, answer in player_answers.items() if p == player]},
        room=request.sid,
    )

    if obviously_lies_game_manager.all_false_submitted(lobby_code):
        all_answers = obviously_lies_game_manager.get_all_answers(lobby_code)
        random.shuffle(all_answers)
        emit("obviously_lies_all_answers", {"answers": all_answers}, room=lobby_code)


@socketio.on("obviously_lies_vote")
def obviously_lies_vote(data):
    lobby_code = data.get("lobbyCode")
    player = data.get("player")
    answer = data.get("answer")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return

    if not obviously_lies_game_manager.games.get(lobby_code):
        emit("error_message", {"message": "Round not started."}, room=request.sid)
        return

    current_votes = lobby_votes.setdefault(lobby_code, {})
    if player in current_votes:
        emit("error_message", {"message": "Vote failed or already voted."}, room=request.sid)
        return

    if player == lobbies[lobby_code]["host"]:
        emit("error_message", {"message": "Host cannot vote."}, room=request.sid)
        return

    success = obviously_lies_game_manager.cast_vote(lobby_code, player, answer)
    if success:
        current_votes[player] = answer
        emit("vote_confirmed", {"answer": answer, "player": player}, room=request.sid)
        emit("update_votes", {"votes": current_votes}, room=lobby_code)
        scores = obviously_lies_game_manager.get_scores(lobby_code)
        emit("update_scores", {"scores": scores}, room=lobby_code)
    else:
        emit("error_message", {"message": "Vote failed or already voted."}, room=request.sid)

    #confirming a vote
    scores = obviously_lies_game_manager.get_scores(lobby_code)
    emit("update_scores", {"scores": scores}, room=lobby_code)

    # Check if ALL non-host players have voted
    all_players = set(lobbies[lobby_code]["players"])
    host = lobbies[lobby_code]["host"]
    eligible_voters = all_players - {host}
    if eligible_voters.issubset(current_votes.keys()):
        # Schedule delayed round end
        def delayed_end_round():
            time.sleep(5)  # 3-second delay before ending the round
            res = round_manager.end_round(lobby_code)
            if res["game_over"]:
                emit("game_over", {"scores": scores}, room=lobby_code)
            else:
                next_round = res["next_round"]
                emit("round_ended", {"next_round": next_round, "scores": scores}, room=lobby_code)
                round_manager.start_round(lobby_code)
                # Reset per-round state for Obviously Lies
                obviously_lies_game_manager.reset_round_state(lobby_code)

        socketio.start_background_task(delayed_end_round)
    
    if obviously_lies_game_manager.all_false_submitted(lobby_code):
        all_answers = obviously_lies_game_manager.get_all_answers(lobby_code)
        random.shuffle(all_answers)
        emit("obviously_lies_all_answers", {"answers": all_answers}, room=lobby_code)

    # When everyone has voted
    if len(current_votes) >= len(lobbies[lobby_code]["players"]) - 1:  # exclude host
        emit("round_ending_soon", {"countdown": 5}, room=lobby_code)
        schedule_round_end(lobby_code, delay=5)

    if len(current_votes) >= len(lobbies[lobby_code]["players"]) - 1:  # exclude host
        emit("round_ending_soon", {"countdown": 5}, room=lobby_code)
        schedule_round_end(lobby_code, delay=5)

@socketio.on("end_round")
def handle_end_round(data):
    lobby_code = data.get("lobbyCode")

    if not lobby_code or lobby_code not in lobbies:
        emit("error_message", {"message": "Lobby not found."}, room=request.sid)
        return

    res = round_manager.end_round(lobby_code)

    if res["game_over"]:
        scores = obviously_lies_game_manager.get_scores(lobby_code)
        emit("game_over", {"scores": scores}, room=lobby_code)
    else:
        # Reset per-round state
        obviously_lies_game_manager.reset_round_state(lobby_code)
        lobby_votes[lobby_code] = {}

        next_round = res["next_round"]
        emit("round_ended", {"next_round": next_round}, room=lobby_code)

        # Start next round
        round_manager.start_round(lobby_code)

def schedule_round_end(lobby_code, delay=5):
    def delayed():
        socketio.sleep(delay)  # non-blocking sleep in Flask-SocketIO
        res = round_manager.end_round(lobby_code)
        summary = obviously_lies_game_manager.end_round(lobby_code)

        if res["game_over"]:
            emit(
                "game_over",
                {"scores": summary["scores"]},
                room=lobby_code
            )
        else:
            emit(
                "round_summary",
                {
                    "roundNumber": res["current_round"],
                    "totalRounds": res["total_rounds"],
                    "summary": summary,
                    "nextRoundIn": delay,
                },
                room=lobby_code,
            )

            # Reset game state for new round
            players = set(lobbies[lobby_code]["players"])
            host = lobbies[lobby_code]["host"]

            # Placeholder Q/A for now
            next_question = f"Auto-generated question {res['current_round']}"
            next_answer = f"Answer {res['current_round']}"

            # Start new round
            round_manager.start_round(lobby_code)
            obviously_lies_game_manager.start_round(
                lobby_code,
                next_question,
                next_answer,
                players,
                host
            )

            # Announce new round
            emit(
                "obviously_lies_round_started",
                {"question": next_question},
                room=lobby_code
            )
    threading.Thread(target=delayed).start()
