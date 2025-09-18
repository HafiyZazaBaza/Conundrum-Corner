class ObviouslyLiesGame:
    def __init__(self):
        self.question = None
        self.correct_answer = None
        self.fake_answers = {}  # sid -> answer
        self.scores = {}
        self.votes = {}

    def set_question(self, socketio, room, question, correct_answer, host):
        self.question = question
        self.correct_answer = correct_answer
        self.fake_answers = {}
        self.votes = {}
        socketio.emit("lies_new_question", {
            "question": self.question,
            "host": host
        }, room=room)

    def submit_fake_answer(self, socketio, room, sid, answer):
        self.fake_answers[sid] = answer
        socketio.emit("lies_answer_submitted", {"sid": sid}, room=room)

    def start_voting(self, socketio, room):
        all_options = list(self.fake_answers.values()) + [self.correct_answer]
        socketio.emit("lies_start_voting", {"options": all_options}, room=room)

    def cast_vote(self, socketio, room, sid, chosen_answer, username):
        self.votes[sid] = chosen_answer
        if chosen_answer == self.correct_answer:
            self.scores[username] = self.scores.get(username, 0) + 1
        else:
            # award point to whoever wrote the lie
            for author_sid, fake in self.fake_answers.items():
                if fake == chosen_answer:
                    self.scores[author_sid] = self.scores.get(author_sid, 0) + 1

    def end_round(self, socketio, room):
        socketio.emit("lies_round_result", {
            "question": self.question,
            "correct_answer": self.correct_answer,
            "fake_answers": self.fake_answers,
            "votes": self.votes,
            "scores": self.scores
        }, room=room)