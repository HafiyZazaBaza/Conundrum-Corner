# conundrum/socket.py
"""
Socket.IO event handlers: lobbies, chat, profanity-block notifications.

Usage:
    In engine.py (where we create socketio), do:

    from conundrum.socket import register_socket_handlers
    register_socket_handlers(socketio)

This file expects a ChatHandler class available at:
    conundrum.utils.chat_handler.ChatHandler
or fallback to utils.chat_handler.ChatHandler if not using package import.

Make sure your ChatHandler.process_message(...) returns a dict like:
    {"blocked": True, "reason": "1man1jar", "severity": 4}
or
    {"blocked": False, "message": "cleaned text"}
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
import random
import string
import traceback

# try both import styles so this file works whether you run as package or not
try:
    from conundrum.utils.chat_handler import ChatHandler
except Exception:
    try:
        from utils.chat_handler import ChatHandler
    except Exception:
        raise ImportError("Could not import ChatHandler. Put chat_handler.py in conundrum/utils or utils/")

# in-memory state (simple; not persistent)
lobbies = {}         # { "ABCD": {"host": "Alice", "players": ["Alice","Bob"], "game_mode": "reverse_guessing", "max_players": 4} }
user_sessions = {}   # { sid: {"username": "...", "lobby": "ABCD"} }

# chat handler instance (loads your JSON and applies rules)
chat_handler = ChatHandler()  # ChatHandler should load its json internally or accept path in ctor


def generate_code(length: int = 4):
    """Generate a unique lobby code (uppercase letters)."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=length))
        if code not in lobbies:
            return code


def get_players_in_lobby(code):
    """Return a list of usernames currently listed in lobbies[code]['players'] if exists."""
    lobby = lobbies.get(code)
    if not lobby:
        return []
    return list(lobby.get("players", []))


def safe_emit_to_sid(event, payload, sid):
    """Emit to a single socket id, catching exceptions so we don't crash the server."""
    try:
        emit(event, payload, to=sid)
    except Exception:
        # log but don't crash
        print(f"[socket] failed emitting {event} to {sid}")
        traceback.print_exc()


def register_socket_handlers(socketio):
    """Register all socket event handlers using the provided socketio instance."""

    @socketio.on("connect")
    def _on_connect():
        print(f"[socket] connect: {request.sid}")

    @socketio.on("disconnect")
    def _on_disconnect():
        sid = request.sid
        info = user_sessions.pop(sid, None)
        if not info:
            print(f"[socket] disconnect (no session): {sid}")
            return

        username = info.get("username")
        lobby_code = info.get("lobby")
        print(f"[socket] disconnect: {username} ({sid}) from lobby {lobby_code}")

        # remove from lobbies list and update others
        if lobby_code and lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            if username in lobby["players"]:
                lobby["players"].remove(username)

            # reassign host if necessary
            if lobby.get("host") == username:
                lobby["host"] = lobby["players"][0] if lobby["players"] else None

            # if lobby empty, delete it
            if not lobby["players"]:
                del lobbies[lobby_code]
                print(f"[socket] lobby {lobby_code} deleted (empty)")
            else:
                # broadcast updated player list
                try:
                    emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)
                except Exception:
                    traceback.print_exc()

        # make sure the socket leaves the room
        try:
            leave_room(lobby_code)
        except Exception:
            pass

    @socketio.on("create_lobby")
    def _on_create_lobby(data):
        """
        data: { username, maxPlayers, gameMode }
        reply to creator: emit('lobby_created', {...}, to=request.sid)
        """
        sid = request.sid
        username = (data.get("username") or "Anonymous").strip()
        try:
            max_players = int(data.get("maxPlayers", 4))
        except Exception:
            max_players = 4
        game_mode = data.get("gameMode") or "reverse_guessing"

        if not username:
            safe_emit_to_sid("error_message", {"message": "Username required."}, sid)
            return

        code = generate_code()
        lobbies[code] = {
            "host": username,
            "players": [username],
            "game_mode": game_mode,
            "max_players": max(2, min(10, max_players))
        }

        # track session
        user_sessions[sid] = {"username": username, "lobby": code}

        # join socket room
        join_room(code)

        # send lobby code only to creator
        safe_emit_to_sid("lobby_created", {"username": username, "lobbyCode": code, "gameMode": game_mode}, sid)

        # broadcast update (creator is in the room)
        try:
            emit("lobby_update", {"players": lobbies[code]["players"], "host": lobbies[code]["host"]}, room=code)
        except Exception:
            traceback.print_exc()

    @socketio.on("join_lobby")
    def _on_join_lobby(data):
        """
        data: { username, lobbyCode }
        Replies:
          - to joining client: emit('lobby_joined', {...}, to=request.sid)
          - to joining client on error: emit('error_message', {...}, to=request.sid)
          - broadcast update: emit('lobby_update', {...}, room=lobbyCode)
        """
        sid = request.sid
        username = (data.get("username") or "Anonymous").strip()
        lobby_code = (data.get("lobbyCode") or "").upper().strip()

        if not lobby_code:
            safe_emit_to_sid("error_message", {"message": "Lobby code required."}, sid)
            return

        if lobby_code not in lobbies:
            safe_emit_to_sid("error_message", {"message": "Lobby not found."}, sid)
            return

        lobby = lobbies[lobby_code]

        # if username already exists in lobby, allow rejoin (don't duplicate)
        if username in lobby["players"]:
            user_sessions[sid] = {"username": username, "lobby": lobby_code}
            join_room(lobby_code)
            safe_emit_to_sid("lobby_joined", {"username": username, "lobbyCode": lobby_code, "gameMode": lobby["game_mode"]}, sid)
            # update all in lobby
            emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)
            return

        # check capacity
        if len(lobby["players"]) >= lobby["max_players"]:
            safe_emit_to_sid("error_message", {"message": "Lobby is full."}, sid)
            return

        # add player
        lobby["players"].append(username)
        user_sessions[sid] = {"username": username, "lobby": lobby_code}
        join_room(lobby_code)

        safe_emit_to_sid("lobby_joined", {"username": username, "lobbyCode": lobby_code, "gameMode": lobby["game_mode"]}, sid)

        # broadcast updated players list
        emit("lobby_update", {"players": lobby["players"], "host": lobby["host"]}, room=lobby_code)

    @socketio.on("send_message")
    def _on_send_message(data):
        """
        data: { message } (we prefer using stored user_sessions for username & lobby)
        If blocked: emit('blocked_message', {...}, to=request.sid)  (only to sender)
        If allowed: emit('receive_message', { username, message }, room=lobby)
        """
        sid = request.sid
        sess = user_sessions.get(sid, {})
        username = sess.get("username") or data.get("username") or "Anonymous"
        lobby_code = sess.get("lobby") or data.get("lobbyCode")
        message = (data.get("message") or "").strip()

        if not lobby_code:
            safe_emit_to_sid("error_message", {"message": "You are not in a lobby."}, sid)
            return
        if not message:
            return  # empty nothing to do

        # run through chat handler (which wraps profanity filter)
        try:
            result = chat_handler.process_message(message)
        except Exception:
            # If the chat handler crashes, do not broadcast raw input
            traceback.print_exc()
            safe_emit_to_sid("error_message", {"message": "Server filter error."}, sid)
            return

        if result.get("blocked"):
            # only notify the sender (outside chatbox)
            safe_emit_to_sid("blocked_message", {"text": "❌ Your message was blocked for profanity."}, sid)
            return

        # allowed path -> message may be censored or original
        clean_text = result.get("message") if "message" in result else message
        emit("receive_message", {"username": username, "message": clean_text}, room=lobby_code)

    @socketio.on("start_game")
    def _on_start_game(data):
        """
        data: { lobbyCode, username, mode }
        Only the host can trigger. Broadcasts 'game_started' to room.
        """
        sid = request.sid
        lobby_code = (data.get("lobbyCode") or "").upper()
        username = data.get("username")

        if not lobby_code or lobby_code not in lobbies:
            safe_emit_to_sid("error_message", {"message": "Lobby not found."}, sid)
            return

        lobby = lobbies[lobby_code]
        if lobby.get("host") != username:
            safe_emit_to_sid("error_message", {"message": "Only host can start the game."}, sid)
            return

        # notify everyone
        emit("game_started", {"mode": data.get("mode", lobby.get("game_mode"))}, room=lobby_code)

    # end register_socket_handlers
