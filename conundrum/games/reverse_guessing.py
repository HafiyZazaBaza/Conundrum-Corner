# conundrum/games/reverse_guessing.py

class ReverseGuessingGame:
    def __init__(self):
        # Store game state keyed by lobby_code
        self.games = {}

    def start_round(self, lobby_code, answer, correct_question, players, host=None):
        # Exclude host from players eligible for scoring
        eligible_players = set(players) - {host} if host else set(players)
        self.games[lobby_code] = {
            "answer": answer,  # host-provided answer
            "correct_question": correct_question,  # host-provided correct question
            "players": set(players),
            "submitted_questions": {},  
            "finished_submitting": set(),
            "votes": {correct_question: set()},  
            "question_to_player": {correct_question: None},  
            "scores": {player: 0 for player in eligible_players},
            "host": host,
        }

    def submit_question(self, lobby_code, player, guessed_question):
        game = self.games.get(lobby_code)
        if not game:
            return False
        if player in game["players"] and player not in game["submitted_questions"]:
            game["submitted_questions"][player] = guessed_question
            game["finished_submitting"].add(player)
            if guessed_question not in game["votes"]:
                game["votes"][guessed_question] = set()
            # Track player who submitted question
            game["question_to_player"][guessed_question] = player
            return True
        return False

    def all_questions_submitted(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return False
        return game["finished_submitting"] == game["players"]

    def get_all_questions(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return []
        for ques in game["submitted_questions"].values():
            if ques not in game["votes"]:
                game["votes"][ques] = set()
        result = list(game["submitted_questions"].values())
        result.append(game["correct_question"])
        return sorted(result)

    def get_votes_for_question(self, lobby_code, question):
        game = self.games.get(lobby_code)
        if not game:
            return 0
        return len(game["votes"].get(question, []))

    def cast_vote(self, lobby_code, player, question):
        game = self.games.get(lobby_code)
        if not game or player not in game["players"] or player == game.get("host"):
            return False
        # Check if player already voted this round
        for voters in game["votes"].values():
            if player in voters:
                return False
        # Question must be in vote options
        if question not in game["votes"]:
            return False
        # Cannot vote for own submitted question
        question_owner = game["question_to_player"].get(question)
        if question_owner == player:
            return False
        # Vote
        game["votes"][question].add(player)

        # Score updates:
        # If voted on a submitted question, the submitter gains a point (if not host)
        if question_owner is not None and question_owner != game.get("host"):
            game["scores"][question_owner] += 4
        # If voted on the correct question, the voter gains a point (if not host)
        if question == game["correct_question"] and player != game.get("host"):
            game["scores"][player] += 5

        return True

    def has_player_voted(self, lobby_code, player):
        game = self.games.get(lobby_code)
        if not game:
            return False
        for voters in game["votes"].values():
            if player in voters:
                return True
        return False

    def get_submitted_questions(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("submitted_questions", {})

    def get_scores(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        return game.get("scores", {})

    def end_round(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return {}
        summary = {
         "scores": game["scores"].copy(),
         "votes": {ans: list(voters) for ans, voters in game["votes"].items()},
         "question": game.get("question") if hasattr(game, "question") else None,
         "answer": game.get("answer") if hasattr(game, "answer") else None
        }   
        return summary

    def reset_round_state(self, lobby_code):
        game = self.games.get(lobby_code)
        if not game:
            return
        game.update({
            "submitted_questions": {},
            "finished_submitting": set(),
            "votes": {game["correct_question"]: set()},
            "question_to_player": {game["correct_question"]: None},
        })
