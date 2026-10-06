import hashlib
import hmac
import secrets

import streamlit as st


def hash_password(password):
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120000
    )

    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


def verify_password(password, stored_password):
    try:
        salt_hex, hash_hex = stored_password.split(
            ":",
            1
        )

        salt = bytes.fromhex(
            salt_hex
        )

        expected_hash = bytes.fromhex(
            hash_hex
        )

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            120000
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except (
        ValueError,
        TypeError
    ):
        return False


def initialize_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "users" not in st.session_state:
        st.session_state.users = {}


def register_user(
    username,
    email,
    password
):
    username = username.strip()
    email = email.strip().lower()

    if not username:
        return False, "Username is required."

    if not email:
        return False, "Email is required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    for user in st.session_state.users.values():

        if user["username"].lower() == username.lower():
            return False, "Username already exists."

        if user["email"].lower() == email:
            return False, "Email already exists."

    user_id = secrets.token_hex(16)

    st.session_state.users[user_id] = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": hash_password(password)
    }

    return True, "Account created successfully."


def login_user(
    email,
    password
):
    email = email.strip().lower()

    for user in st.session_state.users.values():

        if user["email"] == email:

            if verify_password(
                password,
                user["password_hash"]
            ):
                st.session_state.authenticated = True
                st.session_state.user = user

                return True, "Login successful."

            return False, "Incorrect password."

    return False, "Account not found."


def logout_user():
    st.session_state.authenticated = False
    st.session_state.user = None


def is_authenticated():
    return bool(
        st.session_state.get(
            "authenticated",
            False
        )
    )


def current_user():
    return st.session_state.get(
        "user"
    )