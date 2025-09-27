# conundrum/games/emoji_translation.py

class EmojiTranslationGame:
    def __init__(self):
        # Stores game state keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, emoji_prompt, players, host=None):
        # Exclude host from players eligible for scoring
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "emoji_prompt": emoji_prompt,          # The emoji string input by host
            "players": set(players),
            "guesses": {},                         # player -> guessed sentence
            "finished_submitting": set(),
            "votes": {},                          # guess -> set of players who voted for it
            "guess_to_player": {},                 # guess -> player who submitted it
            "scores": {player: 0 for player in eligible_players},  # only non-host players score
            "host": host,
        }

    def submit_guess(self, lobby_code, player, guess):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["guesses"]:
            game["guesses"][player] = guess
            game["finished_submitting"].add(player)
            if guess not in game["votes"]:
                game["votes"][guess] = set()
            game["guess_to_player"][guess] = player
            return True
        return False

    def all_guesses_submitted(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return False
        # All players except the host must submit guess
        players_to_submit = game["players"] - {game["host"]} if game["host"] else game["players"]
        return game["finished_submitting"] == players_to_submit

    def get_all_guesses(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return []
        # Return all guesses submitted sorted alphabetically
        return sorted(game["guesses"].values())

    def get_votes_for_guess(self, lobby_code, guess):
        game = self.games.get(lobby_code)
        if not game:
            return 0
        return len(game["votes"].get(guess, []))

    def cast_vote(self, lobby_code, player, guess):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player not in game["players"]:
            return False
        # Host cannot vote
        if player == game.get("host"):
            return False
        # Player can vote only once per round
        for voters in game["votes"].values():
            if player in voters:
                return False
        if guess not in game["votes"]:
            return False
        # Prevent voting on one's own guess
        guess_owner = game["guess_to_player"].get(guess)
        if guess_owner == player:
            return False
        # Cast vote
        game["votes"][guess].add(player)

        # Owner of the guess gets a point when their guess is voted
        if guess_owner and guess_owner != game.get("host"):
            game["scores"][guess_owner] += 1

        return True

    def has_player_voted(self, lobby_code, player):
        game = self.games.get(lobby_code)
        if not game:
            return False
        for voters in game["votes"].values():
            if player in voters:
                return True
        return False

    def get_submitted_guesses(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("guesses", {})

    def get_scores(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("scores", {})

    def end_round(self, lobby_code):
        """Finalize round but do not delete scores."""
        game = self.games.get(lobby_code)
        if not game:
            return {}
        summary = {
            "game": "emoji_translation",
            "scores": game["scores"].copy(),
            "details": {
                "emoji_prompt": game["emoji_prompt"],
                "guesses": game["guesses"].copy(),
                "votes": {guess: list(voters) for guess, voters in game["votes"].items()},
            },
        }
        return summary

    def reset_round_state(self, lobby_code):
        """Reset per-round state but keep scores intact."""
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "guesses": {},
            "finished_submitting": set(),
            "votes": {},
            "guess_to_player": {},
        })
