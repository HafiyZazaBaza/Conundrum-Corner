import random

class EmojiTranslationGame:
    def __init__(self):
        self.game_data = {}  # Stores game data for each lobby
        self.players = []

    def start_game(self, lobby_code, players, prompt_list):
        """Start the Emoji Translation Game for a lobby."""
        self.game_data[lobby_code] = {
            "players": players,
            "round": 1,
            "prompts": prompt_list,
            "current_prompt": None,
            "emoji_translations": {},
            "player_guesses": {},
            "scores": {player: 0 for player in players},  # Initialize scores for players
            "phase": "translation",  # Initial phase is translation
        }
        self.players = players

    def get_prompt(self, lobby_code):
        """Get the current prompt for the Emoji Translation game."""
        game = self.game_data.get(lobby_code)
        if game and game['round'] <= len(game['prompts']):
            prompt = game['prompts'][game['round'] - 1]
            game['current_prompt'] = prompt
            return prompt
        return None

    def submit_translation(self, lobby_code, player, translation):
        """Handle the emoji translation submitted by a player."""
        game = self.game_data.get(lobby_code)
        if game:
            game['emoji_translations'][player] = translation
            if len(game['emoji_translations']) == len(game['players']):
                return self.next_round(lobby_code, phase="guessing")
        return None

    def next_round(self, lobby_code, phase="translation"):
        """Advance to the next round and handle guesses."""
        game = self.game_data.get(lobby_code)
        if game:
            game['round'] += 1
            game['player_guesses'] = {}
            game['phase'] = phase
            if game['round'] > len(game['prompts']):
                return self.end_game(lobby_code)
            return self.get_prompt(lobby_code)
        return None

    def submit_guess(self, lobby_code, player, guess):
        """Handle the guess submitted by a player for the emoji translation."""
        game = self.game_data.get(lobby_code)
        if game and game['round'] > 0:
            correct_translation = game['emoji_translations'].get(player)
            if guess == correct_translation:  # Check if the guess is correct
                game['scores'][player] += 1  # Increment the score
            game['player_guesses'][player] = guess
            if len(game['player_guesses']) == len(game['players']):
                return self.next_round(lobby_code, phase="translation")
        return None

    def end_game(self, lobby_code):
        """End the game and show results."""
        game = self.game_data.get(lobby_code)
        if game:
            return "Game Over", game['scores']
        return {}, {}

