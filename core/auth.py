import bcrypt
from dataclasses import dataclass

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode('utf-8'), h.encode('utf-8'))
    except Exception:
        return False


def require_login() -> dict:
    import streamlit as st
    if not st.session_state.get("auth"):
        try:
            st.switch_page("app.py")
        except Exception:
            st.warning("Bitte zuerst anmelden.")
            st.stop()
    return st.session_state.get("auth")
