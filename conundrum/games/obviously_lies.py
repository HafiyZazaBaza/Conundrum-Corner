class ObviouslyLiesGame:
    def __init__(self):
        # Stores game state keyed by lobby_code
        self.games = {}

    def start_game(self, lobby_code, question, correct_answer, players, host=None):
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
            "host": host,
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
        if player == game.get("host"):
            return False
        for voters in game["votes"].values():
            if player in voters:
                return False
        if answer not in game["votes"]:
            return False
        answer_owner = game["answer_to_player"].get(answer)
        if answer_owner == player:
            return False
        game["votes"][answer].add(player)

        # Update scores
        if answer_owner is not None and answer_owner != game.get("host"):
            # If voted a false answer, owner gets a point
            game["scores"][answer_owner] += 1
        if answer == game["correct_answer"] and player != game.get("host"):
            # If voted correct answer, voter gets a point
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

    def reset_game_state(self, lobby_code):
        # Reset per-game state but keep scores intact
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "false_answers": {},
            "finished_submitting": set(),
            "votes": {game["correct_answer"]: set()},
            "answer_to_player": {game["correct_answer"]: None},
        })
