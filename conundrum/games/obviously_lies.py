# conundrum/games/obviously_lies.py
class ObviouslyLiesGame:
    def __init__(self):
        # key: lobby_code -> value: game data dict
        self.games = {}

    def start_round(self, lobby_code, question, correct_answer, players):
        self.games[lobby_code] = {
            "question": question,
            "correct_answer": correct_answer,
            "players": set(players),
            # player -> false answer
            "false_answers": {},
            # player -> selected answer
            "selections": {},
            "finished_submitting": set(),
            "finished_selecting": set(),
        }

    def submit_false_answer(self, lobby_code, player, false_answer):
        game = self.games[lobby_code]
        if player in game["players"] and player not in game["false_answers"]:
            game["false_answers"][player] = false_answer
            game["finished_submitting"].add(player)
            return True
        return False

    def all_false_submitted(self, lobby_code):
        game = self.games[lobby_code]
        return game["finished_submitting"] == game["players"]

    def get_all_answers(self, lobby_code):
        game = self.games[lobby_code]
        # Compose the answer list: correct answer + all false answers, anonymous
        result = list(game["false_answers"].values())
        result.append(game["correct_answer"])
        return sorted(result)  # or shuffle before sending

    def submit_selection(self, lobby_code, player, selected_answer):
        game = self.games[lobby_code]
        if player in game["players"] and player not in game["selections"]:
            game["selections"][player] = selected_answer
            game["finished_selecting"].add(player)
            return True
        return False

    def all_selected(self, lobby_code):
        game = self.games[lobby_code]
        return game["finished_selecting"] == game["players"]

    def calculate_scores(self, lobby_code):
        game = self.games[lobby_code]
        scores = {p: 0 for p in game["players"]}

        # Scores: players who picked correct answer score 1
        for player, selected in game["selections"].items():
            if selected == game["correct_answer"]:
                scores[player] += 1

        # Players gain points if others pick their false answers
        for player, false_answer in game["false_answers"].items():
            for other_player, selected in game["selections"].items():
                if other_player != player and selected == false_answer:
                    scores[player] += 1

        return scores

    def end_round(self, lobby_code):
        if lobby_code in self.games:
            del self.games[lobby_code]
