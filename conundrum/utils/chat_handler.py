from profanity_filter import ProfanityFilter

class ChatHandler:
    def __init__(self):
        self.profanity_filter = ProfanityFilter(block_threshold=3)
        self.profanity_filter.load_words("data/profanity.json")

    def handle_message(self, user, text):
        """Process incoming chat message."""
        result = self.profanity_filter.check_message(text)

        if not result["allowed"]:
            # ❌ Profanity too severe → block message
            return {
                "type": "system",
                "text": "❌ Message blocked for profanity.",
                "user": "system"
            }

        # ✅ Allowed (possibly censored) → send normally
        return {
            "type": "chat",
            "text": result["text"],
            "user": user
        }
