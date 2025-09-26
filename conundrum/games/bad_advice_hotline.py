class BadAdviceHotlineGame:
    def __init__(self):
        # Store game states keyed by lobby_code
        self.games = {}

    def start_game(self, lobby_code, question, players, host=None):
        # Initialize game state for a lobby; no round tracking
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "question": question,
            "players": set(players),
            "bad_advice_answers": {},  # player -> bad advice answer
            "finished_submitting": set(),
            "votes": {},  # answer -> set of players who voted for it
            "answer_to_player": {},  # answer -> player who submitted it
            "scores": {player: 0 for player in eligible_players},  # exclude host
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

        if answer_owner is not None and answer_owner != game.get("host"):
            game["scores"][answer_owner] += 1

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

    def reset_game_state(self, lobby_code):
        # Reset everything except player list, scores, and host
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "question": None,
            "bad_advice_answers": {},
            "finished_submitting": set(),
            "votes": {},
            "answer_to_player": {},
        })
