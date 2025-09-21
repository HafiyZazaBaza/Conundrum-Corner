# conundrum/games/obviously_lies.py


class ObviouslyLiesGame:
    def __init__(self):
        # Stores game state keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, question, correct_answer, players, host=None):
        # Exclude host from players eligible for scoring
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "question": question,
            "correct_answer": correct_answer,
            "players": set(players),
            "false_answers": {},  # player -> false answer
            "finished_submitting": set(),
            "votes": {correct_answer: set()},  # answer -> set of players who voted for it
            "answer_to_player": {correct_answer: None},  # answer -> player who submitted (None for correct answer)
            "scores": {player: 0 for player in eligible_players},  # only non-host players score
            "host": host,  # remember the host
        }

    def submit_false_answer(self, lobby_code, player, false_answer):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["false_answers"]:
            game["false_answers"][player] = false_answer
            game["finished_submitting"].add(player)
            if false_answer not in game["votes"]:
                game["votes"][false_answer] = set()
            # Track which player submitted which answer
            game["answer_to_player"][false_answer] = player
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
        for ans in game["false_answers"].values():
            if ans not in game["votes"]:
                game["votes"][ans] = set()
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
        # Host cannot vote
        if player == game.get("host"):
            return False
        # Player can only vote once per round
        for voters in game["votes"].values():
            if player in voters:
                return False
        # Check if answer is valid in this round
        if answer not in game["votes"]:
            return False
        # Prevent voting on one's own false answer
        answer_owner = game["answer_to_player"].get(answer)
        if answer_owner == player:
            return False
        # Cast the vote
        game["votes"][answer].add(player)

        # Update scores:
        # If voted a false answer, owner of false answer gets a point (if not host)
        if answer_owner is not None and answer_owner != game.get("host"):
            game["scores"][answer_owner] += 1
        # If voted the correct answer, voter gets a point (if not host)
        if answer == game["correct_answer"] and player != game.get("host"):
            game["scores"][player] += 1

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

    def get_scores(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("scores", {})

    def end_round(self, lobby_code):
        if lobby_code in self.games:
            del self.games[lobby_code]
