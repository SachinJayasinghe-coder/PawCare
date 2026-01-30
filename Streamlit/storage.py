# storage.py
import json, os

USERS_FILE = "users.json"

def load_users(default_users):
    #Load users from users.json; if missing/corrupt, seed with defaults.
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else default_users.copy()
        except Exception:
            return default_users.copy()
    # If file doesn't exist, create it with defaults
    save_users(default_users)
    return default_users.copy()

def save_users(users_list):
    #Save users to users.json (pretty-printed).
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_list, f, indent=2)

DAYCARE_FILE = "daycare.json"

def load_daycare(default_list=None):
    if default_list is None:
        default_list = []
    if os.path.exists(DAYCARE_FILE):
        try:
            with open(DAYCARE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else default_list.copy()
        except Exception:
            return default_list.copy()
    save_daycare(default_list)
    return default_list.copy()

def save_daycare(daycare_list):
    with open(DAYCARE_FILE, "w", encoding="utf-8") as f:
        json.dump(daycare_list, f, indent=2)

# --- PETS section ---
PETS_FILE = "pets.json"

def load_pets(default_list=None):
    if default_list is None:
        default_list = []
    try:
        import os, json
        if os.path.exists(PETS_FILE):
            with open(PETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else default_list.copy()
    except Exception:
        pass
    # seed file if missing/corrupt
    save_pets(default_list)
    return default_list.copy()

def save_pets(pets_list):
    import json
    with open(PETS_FILE, "w", encoding="utf-8") as f:
        json.dump(pets_list, f, indent=2)