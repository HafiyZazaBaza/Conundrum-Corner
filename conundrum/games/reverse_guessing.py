import random

class ReverseGuessingGame:
    def __init__(self):
        self.current_answer = None
        self.questions = []     # [{ "sid": str, "username": str, "question": str }]
        self.scores = {}        # { username: points }
        self.active_round = {}  # { "question": str, "author": str, "guesser": str }

        self.answer_pool = [
            "The Moon", "Pizza", "Albert Einstein",
            "Minecraft", "Eiffel Tower", "Shrek"
        ]

    def start_round(self, socketio, room, players):
        """Pick a random answer and reset the round"""
        self.current_answer = random.choice(self.answer_pool)
        self.questions = []
        self.active_round = {}

        for user in players.values():
            self.scores.setdefault(user, 0)

        socketio.emit("reverse_new_answer", {"answer": self.current_answer}, room=room)

    def submit_question(self, socketio, room, sid, username, question):
        self.questions.append({"sid": sid, "username": username, "question": question})
        socketio.emit("reverse_question_submitted", {"username": username}, room=room)

    def ask_question(self, socketio, room, players):
        if not self.questions:
            socketio.emit("reverse_round_end", {"scores": self.scores}, room=room)
            return

        q = self.questions.pop(0)
        possible_guessers = [u for u in players.values() if u != q["username"]]
        if not possible_guessers:
            self.ask_question(socketio, room, players)
            return

        guesser = random.choice(possible_guessers)
        self.active_round = {"question": q["question"], "author": q["username"], "guesser": guesser}

        socketio.emit("reverse_ask_player", {
            "question": q["question"], "author": q["username"], "target": guesser
        }, room=room)

    def guess_answer(self, socketio, room, username, guess, players):
        if not self.active_round:
            return

        correct = guess.strip().lower() == self.current_answer.lower()
        if correct:
            self.scores[username] = self.scores.get(username, 0) + 1
            self.scores[self.active_round["author"]] = self.scores.get(self.active_round["author"], 0) + 1
            socketio.emit("reverse_correct", {
                "guesser": username,
                "author": self.active_round["author"],
                "guess": guess,
                "answer": self.current_answer,
                "scores": self.scores
            }, room=room)
        else:
            socketio.emit("reverse_wrong", {
                "username": username,
                "guess": guess,
                "answer": self.current_answer
            }, room=room)

        self.active_round = {}
        self.ask_question(socketio, room, players)
