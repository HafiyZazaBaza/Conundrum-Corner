# conundrum/games/emoji_translation.py

class EmojiTranslationGame:
    def __init__(self):
        # Stores game state keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, emoji_prompt, correct_sentence, players, host=None):
        # Exclude host from players eligible for scoring
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "emoji_prompt": emoji_prompt,
            "correct_sentence": correct_sentence,
            "players": set(players),
            "submitted_sentences": {},  # player -> sentence guess
            "finished_submitting": set(),
            "votes": {correct_sentence: set()},  # sentence -> set of players who voted for it
            "sentence_to_player": {correct_sentence: None},  # sentence -> submitting player (None for correct)
            "scores": {player: 0 for player in eligible_players},  # only non-host players score
            "host": host,
        }

    def submit_sentence(self, lobby_code, player, sentence):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["submitted_sentences"]:
            game["submitted_sentences"][player] = sentence
            game["finished_submitting"].add(player)
            if sentence not in game["votes"]:
                game["votes"][sentence] = set()
            # Track which player submitted which sentence
            game["sentence_to_player"][sentence] = player
            return True
        return False

    def all_sentences_submitted(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return False
        return game["finished_submitting"] == game["players"]

    def get_all_sentences(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return []
        # Ensure all submitted sentences are in votes dict
        for sentence in game["submitted_sentences"].values():
            if sentence not in game["votes"]:
                game["votes"][sentence] = set()
        result = list(game["submitted_sentences"].values())
        result.append(game["correct_sentence"])
        return sorted(result)

    def get_votes_for_sentence(self, lobby_code, sentence):
        game = self.games.get(lobby_code)
        if not game:
            return 0
        return len(game["votes"].get(sentence, []))

    def cast_vote(self, lobby_code, player, sentence):
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
        # Check if sentence is valid in this round
        if sentence not in game["votes"]:
            return False
        # Prevent voting on one's own sentence guess
        sentence_owner = game["sentence_to_player"].get(sentence)
        if sentence_owner == player:
            return False
        # Cast the vote
        game["votes"][sentence].add(player)

        # Update scores:
        # If voted a non-correct sentence, owner of that sentence gets a point (if not host)
        if sentence_owner is not None and sentence_owner != game.get("host"):
            game["scores"][sentence_owner] += 1
        # If voted the correct sentence, voter gets a point (if not host)
        if sentence == game["correct_sentence"] and player != game.get("host"):
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

    def get_submitted_sentences(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("submitted_sentences", {})

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
            "votes": {sentence: list(voters) for sentence, voters in game["votes"].items()},
        }
        return summary

    def reset_round_state(self, lobby_code):
        """Reset per-round state but keep scores intact."""
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "submitted_sentences": {},
            "finished_submitting": set(),
            "votes": {game["correct_sentence"]: set()},
            "sentence_to_player": {game["correct_sentence"]: None},
        })
