import random

reverse_games = {}  
# reverse_games[room] = {
#   "current_answer": str,
#   "questions": [],   # [{ "sid": str, "username": str, "question": str }]
#   "scores": {},      # { username: points }
#   "players": {}      # { sid: username }
#   "active_round": {} # { "question": str, "author": username, "guesser": username }
# }

def start_reverse_game(socketio, room, players):
    """Start a new round with a random answer"""
    answers = ["The Moon", "Pizza", "Albert Einstein", "Minecraft", "Eiffel Tower", "Shrek"]
    answer = random.choice(answers)

    reverse_games[room] = {
        "current_answer": answer,
        "questions": [],
        "scores": {username: 0 for username in players.values()},
        "players": players,
        "active_round": {}
    }

    socketio.emit("reverse_new_answer", {
        "answer": answer
    }, room=room)


def submit_question(socketio, room, sid, username, question):
    """Player submits a question for the current answer"""
    game = reverse_games.get(room)
    if not game: return

    game["questions"].append({
        "sid": sid,
        "username": username,
        "question": question
    })

    socketio.emit("reverse_question_submitted", {
        "username": username,
        "question": question
    }, room=room)


def ask_question(socketio, room):
    """Ask the next question (removes it from list)."""
    game = reverse_games.get(room)
    if not game or not game["questions"]: 
        # No more questions → end round
        socketio.emit("reverse_round_end", {
            "scores": game["scores"]
        }, room=room)
        return

    # Take the first question in queue
    q = game["questions"].pop(0)

    # Pick a random guesser who is NOT the author
    possible_guessers = [u for sid, u in game["players"].items() if u != q["username"]]
    if not possible_guessers:
        ask_question(socketio, room)  # skip invalid case
        return

    guesser = random.choice(possible_guessers)

    game["active_round"] = {
        "question": q["question"],
        "author": q["username"],
        "guesser": guesser
    }

    socketio.emit("reverse_ask_player", {
        "question": q["question"],
        "author": q["username"],
        "target": guesser
    }, room=room)


def check_answer(socketio, room, sid, username, guess):
    """Check if guess matches the answer. Award points, then move to next question."""
    game = reverse_games.get(room)
    if not game: return

    round_info = game["active_round"]
    if not round_info: return

    correct = guess.strip().lower() == game["current_answer"].lower()
    if correct:
        # Award points to both
        game["scores"][username] = game["scores"].get(username, 0) + 1
        game["scores"][round_info["author"]] = game["scores"].get(round_info["author"], 0) + 1

        socketio.emit("reverse_correct", {
            "guesser": username,
            "author": round_info["author"],
            "guess": guess,
            "answer": game["current_answer"],
            "scores": game["scores"]
        }, room=room)
    else:
        socketio.emit("reverse_wrong", {
            "username": username,
            "guess": guess,
            "answer": game["current_answer"]
        }, room=room)

    # reset round info
    game["active_round"] = {}

    # Automatically move to the next question
    ask_question(socketio, room)
