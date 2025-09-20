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
            "false_answers": {},  # player -> false answer
            "finished_submitting": set(),
            "votes": {},  # answer -> set of players who voted for it
        }


    def submit_false_answer(self, lobby_code, player, false_answer):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["false_answers"]:
            game["false_answers"][player] = false_answer
            game["finished_submitting"].add(player)
            # Initialize vote set for this answer
            game["votes"][false_answer] = set()
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
        # Also ensure votes dict has entry for correct_answer
        if game["correct_answer"] not in game["votes"]:
            game["votes"][game["correct_answer"]] = set()
        result = list(game["false_answers"].values())
        result.append(game["correct_answer"])
        return sorted(result)


    def get_votes_for_answer(self, lobby_code, answer):
        game = self.games.get(lobby_code)
        if not game:
            return 0
        return len(game["votes"].get(answer, []))


    def cast_vote(self, lobby_code, player, answer):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player not in game["players"]:
            return False
        # Player can only vote once per round
        # Check if player already voted on any answer: disallow multiple votes
        for voters in game["votes"].values():
            if player in voters:
                return False
        # Check if answer is valid in this round
        if answer not in game["votes"]:
            return False
        # Cast the vote
        game["votes"][answer].add(player)
        return True


    def has_player_voted(self, lobby_code, player):
        game = self.games.get(lobby_code)
        if not game:
            return False
        for voters in game["votes"].values():
            if player in voters:
                return True
        return False


    def get_submitted_false_answers(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("false_answers", {})


    def end_round(self, lobby_code):
        if lobby_code in self.games:
            del self.games[lobby_code]
