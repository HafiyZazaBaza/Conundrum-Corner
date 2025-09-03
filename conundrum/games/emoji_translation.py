import random

class EmojiTranslationGame:
    def __init__(self):
        self.prompts = [
            "Run very far away",
            "Eat pizza at midnight",
            "Climb a tall mountain",
            "Watch a scary movie",
            "Build a robot"
        ]
        self.rounds = []      # [{"prompt": str, "emoji": str, "guess": str}]
        self.current_prompt = None
        self.scores = {}

    def start_round(self, socketio, room, players):
        self.current_prompt = random.choice(self.prompts)
        self.rounds = []

        for user in players.values():
            self.scores.setdefault(user, 0)

        socketio.emit("emoji_new_prompt", {"prompt": self.current_prompt}, room=room)

    def submit_translation(self, socketio, room, sid, emoji_string):
        self.rounds.append({"prompt": self.current_prompt, "emoji": emoji_string, "guess": None})
        socketio.emit("emoji_translation_submitted", {"sid": sid}, room=room)

    def submit_guess(self, socketio, room, sid, guess, username):
        if not self.rounds:
            return
        self.rounds[-1]["guess"] = guess
        # simple scoring: +1 if guess contains a word from prompt
        if any(word.lower() in guess.lower() for word in self.current_prompt.split()):
            self.scores[username] = self.scores.get(username, 0) + 1
        socketio.emit("emoji_guess_result", {"guess": guess, "scores": self.scores}, room=room)

    def end_round(self, socketio, room):
        socketio.emit("emoji_round_end", {"rounds": self.rounds, "scores": self.scores}, room=room)
