import streamlit as st
import auth_views
import storage
import daycare_view
import pets_view
import appointments_view
from urllib.parse import urlparse, parse_qs


# ---- Predefined data ----
OWNER = {"username": "owner123", "password": "ownPass", "role": "owner"}

DEFAULT_USERS = [
    {"full_name": "Induwara Wijayarathne", "username": "induwarawij", "password": "induwara123", "role": "user"},
    {"full_name": "Dilina Malshika", "username": "dilina", "password": "dilina123", "role": "user"},
]


def main():
    # --- Parse the URL to detect ?page= parameter ---
    query_params = st.query_params
    page = ""
    if "page" in query_params:
        val = query_params.get("page")
        page = val[0].lower() if isinstance(val, list) else val.lower()

    # ---- Session initialization ----
    ss = st.session_state
    ss.logged_user = ss.get("logged_user", None)
    ss.auth_view = ss.get("auth_view", "login")  # "login" or "register"
    ss.users = ss.get("users", storage.load_users(DEFAULT_USERS))

    # ---- Handle special entry points (owner login via Flask) ----
    if page == "owner_login":
        st.title("🐾 PawClinic Owner Login")

        # Force show login view for the owner account only
        auth_views.show_login_view(OWNER)
        return

    # ---- Dynamic title ----
    if ss.logged_user is None:
        st.title("🐾 PawClinic Registration" if ss.auth_view == "register" else "🐾 PawClinic Login")
    else:
        st.title("🐾 PawClinic")

    # ---- Auth routing (if logged out) ----
    if ss.logged_user is None:
        if ss.auth_view == "login":
            auth_views.show_login_view(OWNER)
        else:
            auth_views.show_register_view()
        return

    # ---- Logged-in user ----
    user = ss.logged_user
    st.subheader(f"Welcome, {user.get('full_name', user['username'])}! 👋")
    st.caption(f"**Role:** {user['role']}")

    # =========================
    # OWNER DASHBOARD
    # =========================
    if user["role"] == "owner":
        st.sidebar.title("🩺 Owner Dashboard")
        owner_menu = st.sidebar.radio("Go to", ["Daycare Reservations", "Pet Database", "Appointments"], index=0)

        if owner_menu == "Daycare Reservations":
            daycare_view.show_owner_daycare()
        elif owner_menu == "Pet Database":
            pets_view.show_owner_pets()
        elif owner_menu == "Appointments":
            appointments_view.show_owner_appointments()

    # =========================
    # USER DASHBOARD
    # =========================
    else:
        st.sidebar.title("👤 User Dashboard")

        if page == "appointments":
            default_index = 1
        else:
            default_index = 0

        user_menu = st.sidebar.radio("Go to", ["Daycare Packages", "Appointments"], index=default_index)

        if user_menu == "Daycare Packages":
            daycare_view.show_user_daycare()
        elif user_menu == "Appointments":
            appointments_view.show_user_appointments()

    # ---- Log out button ----
    st.sidebar.divider()
    if st.sidebar.button("🚪 Log out"):
        ss.logged_user = None
        st.success("Logged out successfully!")
        st.rerun()


if __name__ == "__main__":
    main()
