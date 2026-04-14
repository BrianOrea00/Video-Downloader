import json
import os
from config import HISTORY_FILE

def save_history(data):
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)

    with open(HISTORY_FILE, "r+") as f:
        history = json.load(f)
        history.append(data)
        f.seek(0)
        json.dump(history, f, indent=4)

def clean_filename(name):
    return "".join(c for c in name if c not in r'\/:*?"<>|')
