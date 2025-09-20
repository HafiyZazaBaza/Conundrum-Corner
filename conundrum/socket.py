from flask_socketio import emit, join_room
from flask import request
from . import socketio
import random
import string
from conundrum.games.obviously_lies import ObviouslyLiesGame


# Lobby state: lobby_code -> lobby data
lobbies = {}


# Obviously Lies game manager instance
obviously_lies_game_manager = ObviouslyLiesGame()



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


    emit("receive_message", {"username": username, "message": message}, room=lobby_code)



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


    if mode == "obviously_lies":
        # Initialize a fresh game instance for this lobby
        obviously_lies_game_manager.end_round(lobby_code)  # Clear existing if any


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
    obviously_lies_game_manager.start_round(lobby_code, question, correct_answer, players)


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


    success = obviously_lies_game_manager.submit_false_answer(lobby_code, player, false_answer)
    if not success:
        emit("error_message", {"message": "Failed to submit false answer."}, room=request.sid)
        return


    # Emit newly submitted false answer anonymously (without player names)
    emit("obviously_lies_false_answer_submitted", {"falseAnswer": false_answer}, room=lobby_code)


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


    success = obviously_lies_game_manager.cast_vote(lobby_code, player, answer)


    if success:
        emit("vote_confirmed", {"answer": answer, "player": player}, room=request.sid)
    else:
        emit("error_message", {"message": "Vote failed or already voted."}, room=request.sid)
