class BadAdviceHotlineGame:
    def __init__(self):
        # Store game states keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, question, players, host=None):
        # Exclude host from players eligible for scoring
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "question": question,
            "players": set(players),
            "bad_advice_answers": {},  
            "finished_submitting": set(),
            "votes": {},  
            "answer_to_player": {},  
            "scores": {player: 0 for player in eligible_players},  # only non-host players score
            "host": host,
        }

    def submit_bad_advice(self, lobby_code, player, bad_advice):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["bad_advice_answers"]:
            game["bad_advice_answers"][player] = bad_advice
            game["finished_submitting"].add(player)
            if bad_advice not in game["votes"]:
                game["votes"][bad_advice] = set()
            # Track which player submitted which answer
            game["answer_to_player"][bad_advice] = player
            return True
        return False

    def all_bad_advice_submitted(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return False
        return game["finished_submitting"] == game["players"]

    def get_all_bad_advice_answers(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return []
        for ans in game["bad_advice_answers"].values():
            if ans not in game["votes"]:
                game["votes"][ans] = set()
        # Only show player's bad advice answers, no "correct" answer
        return sorted(game["bad_advice_answers"].values())

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
        # Prevent voting on one's own bad advice answer
        answer_owner = game["answer_to_player"].get(answer)
        if answer_owner == player:
            return False
        # Cast the vote
        game["votes"][answer].add(player)

        # Update scores:
        # If voted for a bad advice answer, owner of that answer gets a point (excluding host)
        if answer_owner is not None and answer_owner != game.get("host"):
            game["scores"][answer_owner] += 5

        return True

    def has_player_voted(self, lobby_code, player):
        game = self.games.get(lobby_code)
        if not game:
            return False
        for voters in game["votes"].values():
            if player in voters:
                return True
        return False

    def get_submitted_bad_advice(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("bad_advice_answers", {})

    def get_scores(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("scores", {})

    def end_round(self, lobby_code):
        """Finalize round but do not delete scores (RoundManager decides if game ends)."""
        game = self.games.get(lobby_code)
        if not game:
            return {}
        summary = {
            "scores": game["scores"].copy(),
            "votes": {ans: list(voters) for ans, voters in game["votes"].items()},
        }
        return summary

    def reset_round_state(self, lobby_code):
        """Reset per-round state but keep scores intact."""
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "bad_advice_answers": {},
            "finished_submitting": set(),
            "votes": {},
            "answer_to_player": {},
        })
