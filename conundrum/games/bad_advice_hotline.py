import random

class BadAdviceGame:
    def __init__(self):
        self.current_question = None
        self.answers = {}   # sid -> answer
        self.votes = {}     # sid -> voted_sid
        self.scores = {}    # username -> points
        self.round_active = False

        self.questions_pool = [
            "How can I make money quickly?",
            "What’s the best way to study for exams?",
            "How can I impress my crush?",
            "What should I do if I forgot my homework?",
            "How do I pay my student loans fast?"
        ]

    def start_round(self, socketio, room, players):
        if self.round_active:
            return
        self.round_active = True
        self.current_question = random.choice(self.questions_pool)
        self.answers = {}
        self.votes = {}

        for user in players.values():
            self.scores.setdefault(user, 0)

        socketio.emit("badadvice_new_question", {"question": self.current_question}, room=room)

    def submit_answer(self, socketio, room, sid, answer):
        if not self.round_active:
            return
        self.answers[sid] = answer
        socketio.emit("badadvice_answer_submitted", {"player": sid}, room=room)

        # For simplicity, start voting once everyone has answered
        if len(self.answers) >= 2:
            self.start_voting(socketio, room)

    def start_voting(self, socketio, room):
        socketio.emit("badadvice_start_voting", {"answers": self.answers}, room=room)

    def cast_vote(self, socketio, room, sid, voted_sid, players):
        if sid in self.votes:
            return
        self.votes[sid] = voted_sid

        if len(self.votes) >= len(self.answers):
            self.end_round(socketio, room, players)

    def end_round(self, socketio, room, players):
        vote_count = {}
        for voted_sid in self.votes.values():
            vote_count[voted_sid] = vote_count.get(voted_sid, 0) + 1

        for sid, count in vote_count.items():
            username = players.get(sid, "Unknown")
            self.scores[username] = self.scores.get(username, 0) + count

        self.round_active = False
        socketio.emit("badadvice_round_result", {
            "answers": self.answers,
            "votes": self.votes,
            "scores": self.scores
        }, room=room)
