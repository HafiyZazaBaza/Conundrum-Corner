# conundrum/run.py

import os
from conundrum import create_app, socketio

app = create_app()

port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=port, debug=True)