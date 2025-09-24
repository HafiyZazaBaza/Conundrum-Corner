# conundrum/utils/round_manager.py

from typing import Callable, Dict, Optional

class RoundManager:
    def __init__(self):
        # state[lobby_code] = {
        #   "max_rounds": int,
        #   "current_round": int,   # 0 means not started
        #   "round_active": bool,
        #   "finished": bool
        # }
        self.state: Dict[str, Dict] = {}
        # handlers[lobby_code] = {
        #   "on_round_start": callable(lobby_code, round_no) optional,
        #   "on_round_end": callable(lobby_code, round_no) optional,
        #   "reset_round": callable(lobby_code) optional  # clear per-round data (answers/votes) but NOT scores
        # }
        self.handlers: Dict[str, Dict[str, Callable]] = {}

    # -------------------------
    # Registration
    # -------------------------
    def register_lobby(self, lobby_code: str, max_rounds: int = 1, handler: Optional[Dict[str, Callable]] = None):
        self.state[lobby_code] = {
            "max_rounds": max(1, int(max_rounds)),
            "current_round": 0,
            "round_active": False,
            "finished": False,
        }
        if handler:
            self.handlers[lobby_code] = handler.copy()
        else:
            self.handlers.pop(lobby_code, None)

    def unregister_lobby(self, lobby_code: str):
        self.state.pop(lobby_code, None)
        self.handlers.pop(lobby_code, None)

    def set_handler(self, lobby_code: str, handler: Dict[str, Callable]):
        """Install or replace handler for a lobby."""
        if lobby_code not in self.state:
            raise KeyError(f"Lobby {lobby_code} not registered")
        self.handlers[lobby_code] = handler.copy()

    # -------------------------
    # Round lifecycle
    # -------------------------
    def start_game(self, lobby_code: str):
        """Start whole game (initialises current_round=1 and starts first round)."""
        s = self.state.get(lobby_code)
        if not s:
            raise KeyError(f"Lobby {lobby_code} not registered")
        s["finished"] = False
        s["current_round"] = 1
        s["round_active"] = True
        # call handler if present
        h = self.handlers.get(lobby_code, {})
        if callable(h.get("on_round_start")):
            try:
                h["on_round_start"](lobby_code, s["current_round"])
            except Exception:
                # handlers must be resilient; manager should not crash
                pass
        return s["current_round"]

    def start_round(self, lobby_code: str):
        """Start next round (if game already started increments if not active)."""
        s = self.state.get(lobby_code)
        if not s:
            raise KeyError(f"Lobby {lobby_code} not registered")
        if s["finished"]:
            return None
        # if current_round is 0 then start at 1
        if s["current_round"] == 0:
            s["current_round"] = 1
        s["round_active"] = True
        h = self.handlers.get(lobby_code, {})
        if callable(h.get("on_round_start")):
            try:
                h["on_round_start"](lobby_code, s["current_round"])
            except Exception:
                pass
        return s["current_round"]

    def end_round(self, lobby_code: str):
        """
        End the current round:
         - calls handler.on_round_end(lobby_code, current_round) if present
         - calls handler.reset_round(lobby_code) to clear per-round temp state (answers/votes)
         - increments current_round or marks finished
        Returns dict:
         { "game_over": bool, "current_round": int, "next_round": int|None }
        """
        s = self.state.get(lobby_code)
        if not s:
            raise KeyError(f"Lobby {lobby_code} not registered")
        if not s["round_active"]:
            # nothing to end
            return {"game_over": s["finished"], "current_round": s["current_round"], "next_round": None}

        current = s["current_round"]
        h = self.handlers.get(lobby_code, {})

        # allow game to compute results / update scores
        if callable(h.get("on_round_end")):
            try:
                h["on_round_end"](lobby_code, current)
            except Exception:
                pass

        # reset per-round temp state (answers, votes) but NOT the scores
        if callable(h.get("reset_round")):
            try:
                h["reset_round"](lobby_code)
            except Exception:
                pass

        s["round_active"] = False

        # decide next round or finish
        if current >= s["max_rounds"]:
            s["finished"] = True
            return {"game_over": True, "current_round": current, "next_round": None}
        else:
            s["current_round"] = current + 1
            # leave round_active False — caller can call start_round to begin next round
            return {"game_over": False, "current_round": current, "next_round": s["current_round"]}

    def get_state(self, lobby_code: str):
        return self.state.get(lobby_code)

    def is_round_active(self, lobby_code: str) -> bool:
        s = self.state.get(lobby_code)
        return bool(s and s.get("round_active"))

    def is_finished(self, lobby_code: str) -> bool:
        s = self.state.get(lobby_code)
        return bool(s and s.get("finished"))

# single instance for easy import
round_manager = RoundManager()
