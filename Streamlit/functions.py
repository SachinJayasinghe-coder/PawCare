# functions.py

def register_user(users_list, full_name, username, password):
    #Registers a new user if username not taken.
    for u in users_list:
        if u["username"] == username:
            return False
    users_list.append({
        "full_name": full_name,
        "username": username,
        "password": password,
        "role": "user"
    })
    return True


def login_user(owner, users_list, username, password):
    #Checks credentials for owner or user.
    # owner first
    if username == owner["username"] and password == owner["password"]:
        return owner
    # users
    for u in users_list:
        if u["username"] == username and u["password"] == password:
            return u
    return None
