# conundrum/utils/rounds.py

class RoundManager:
    def __init__(self):
        # lobby_code -> {"current_round": int, "total_rounds": int}
        self.rounds = {}

    def setup_lobby(self, lobby_code, total_rounds=5):
        """Initialize round tracking for a lobby."""
        self.rounds[lobby_code] = {
            "current_round": 1,
            "total_rounds": total_rounds,
        }

    def start_round(self, lobby_code):
        """Called at the beginning of a round."""
        lobby = self.rounds.get(lobby_code)
        if not lobby:
            return None
        return {
            "current_round": lobby["current_round"],
            "total_rounds": lobby["total_rounds"],
        }

    def end_round(self, lobby_code):
        """Advance round, return whether game is over."""
        lobby = self.rounds.get(lobby_code)
        if not lobby:
            return {"game_over": True}

        # advance round counter
        lobby["current_round"] += 1

        if lobby["current_round"] > lobby["total_rounds"]:
            return {"game_over": True}
        else:
            return {
                "game_over": False,
                "next_round": lobby["current_round"],
                "total_rounds": lobby["total_rounds"],
            }

    def reset_lobby(self, lobby_code):
        """Remove round tracking when game ends."""
        if lobby_code in self.rounds:
            del self.rounds[lobby_code]


# Singleton instance
round_manager = RoundManager()
