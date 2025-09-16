import json
import re
from .profanity_filter import ProfanityFilter


class ChatHandler:
    def __init__(self, filter_file="data/profanity.json"):
        self.profanity_list = []
        self.active = True
        self.load_filter(filter_file)

    def load_filter(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.profanity_list = json.load(f)
        except Exception as e:
            print(f"[ChatHandler] Failed to load profanity file: {e}")
            self.profanity_list = []

    def process_message(self, message: str):
        """Check if message contains profanity."""
        if not self.active or not message:
            return {"blocked": False, "message": message}

        for entry in self.profanity_list:
            pattern = re.compile(entry["match"], re.IGNORECASE)
            if pattern.search(message):
                return {
                    "blocked": True,
                    "reason": entry["id"],
                    "severity": entry["severity"],
                }

        return {"blocked": False, "message": message}

    def enable(self):
        self.active = True

    def disable(self):
        self.active = False
