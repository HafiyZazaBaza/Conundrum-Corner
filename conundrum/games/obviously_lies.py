# conundrum/games/obviously_lies.py

class ObviouslyLiesGame:
    def __init__(self):
        # Stores game state keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, question, correct_answer, players):
        self.games[lobby_code] = {
            "question": question,
            "correct_answer": correct_answer,
            "players": set(players),
            # player -> false answer
            "false_answers": {},
            "finished_submitting": set(),
        }

    def submit_false_answer(self, lobby_code, player, false_answer):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["false_answers"]:
            game["false_answers"][player] = false_answer
            game["finished_submitting"].add(player)
            return True
        return False

    def all_false_submitted(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return False
        return game["finished_submitting"] == game["players"]

    def get_all_answers(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return []
        result = list(game["false_answers"].values())
        result.append(game["correct_answer"])
        return sorted(result)

    def get_submitted_false_answers(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("false_answers", {})

    def end_round(self, lobby_code):
        if lobby_code in self.games:
            del self.games[lobby_code]
