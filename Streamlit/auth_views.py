# auth_views.py
import streamlit as st
import functions
import storage

def show_login_view(owner):
    #Draws the Login UI and handles login actions.
    st.subheader("Login to PawClinic")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = functions.login_user(owner, st.session_state.users, username, password)
        if user:
            st.session_state.logged_user = user
            st.success(f"Welcome, {user['username']} ({user['role']})!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.write("")  # spacing
    col1, col2 = st.columns([0.75, 0.25])
    with col1:
        st.caption("Don't have an account?")
    with col2:
        if st.button("Register →", key="go_register"):
            st.session_state.auth_view = "register"
            st.rerun()


def show_register_view():
    #Draws the Register UI and handles registration actions (user role only).
    st.subheader("Create New User Account")
    full_name = st.text_input("Full Name")
    new_username = st.text_input("Choose a Username")
    new_password = st.text_input("Choose a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if not full_name or not new_username or not new_password:
            st.warning("Please fill all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            success = functions.register_user(
                st.session_state.users, full_name, new_username, new_password
            )
            if success:
                storage.save_users(st.session_state.users)  # 👈 ADD THIS LINE
                st.success("Account created! You can now log in.")
                st.session_state.auth_view = "login"
                st.rerun()
            else:
                st.error("Username already exists. Try another one.")

    st.write("")
    if st.button("← Back to Login", key="back_login"):
        st.session_state.auth_view = "login"
        st.rerun()
