# --- Build Version: v5.1.4 | generated 2025-10-03 20:58:45 ---
import datetime as dt
import streamlit as st
from core.db import init_db, SessionCtx, UserProfile, get_engine
from core.i18n import t

# DB initialisieren (Schema-Version an deine aktuelle anpassen, z.B. 3)
init_db(schema_version=8)

# Seiten-Setup
st.set_page_config(page_title=t("app_title"), page_icon="🏠", layout="wide")

# ----------------------- SIMPLE LOGIN GATE -----------------------
import streamlit as st
from core.db import ensure_admin_user, SessionCtx, User
from core.auth import hash_password, verify_password

try:
    ensure_admin_user("hannes", hash_password("hannes"), role="admin", email=None, full_name="hannes")
except Exception:
    pass

def _do_login(u, p):
    with SessionCtx() as s:
        user = s.query(User).filter(User.username == u, User.is_active == True).one_or_none()
        if user and verify_password(p, user.password_hash):
            st.session_state.auth = {"username": user.username, "name": user.full_name or user.username, "role": user.role}
            return True
    return False

if not st.session_state.get("auth"):
    st.subheader("Login")
    with st.form("login_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            u = st.text_input("Benutzername", value="", key="login_user")
        with col2:
            p = st.text_input("Passwort", type="password", value="", key="login_pass")
        ok = st.form_submit_button("Anmelden")
    if ok:
        if _do_login(u.strip(), p):
            st.success("Erfolgreich angemeldet.")
            st.rerun()
        else:
            st.error("Benutzername oder Passwort falsch.")
    st.stop()

with st.sidebar:
    st.caption(f"Eingeloggt als: **{st.session_state['auth']['username']}**")
    if st.button("Logout"):
        st.session_state.pop("auth", None)
        st.rerun()
# -----------------------------------------------------------------

# ----------------------- AUTHENTICATION GATE (robust) -----------------------
import os, streamlit as st
try:
    from core.db import ensure_admin_user, load_credentials_for_auth
except Exception:
    # Fallback: define dummy creds
    def ensure_admin_user(*args, **kwargs): pass
    def load_credentials_for_auth(): return {"usernames": {}}
from core.auth import hash_password

COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "immo_auth")
COOKIE_KEY  = os.getenv("AUTH_COOKIE_KEY", "change-this-dev-key")
COOKIE_DAYS = int(os.getenv("AUTH_COOKIE_DAYS", "30"))

# Default admin bootstrap (hannes/hannes)
try:
    ensure_admin_user("hannes", hash_password("hannes"), role="admin", email=None, full_name="hannes")
except Exception as _e:
    st.warning("Admin-Bootstrap konnte nicht ausgeführt werden. Prüfe Datenbank-Setup.")

_credentials = load_credentials_for_auth()
_auth = stauth.Authenticate(_credentials, COOKIE_NAME, COOKIE_KEY, COOKIE_DAYS)

try:
    name, auth_status, username = _auth.login('Login', location='main')
except Exception:
    name, auth_status, username = _auth.login('Login', location='sidebar')
if auth_status != True:
    st.stop()

with st.sidebar:
    _auth.logout("Logout")
    st.caption(f"Eingeloggt als: **{username}**")
# ---------------------------------------------------------------------------

# --- Hide Wohnung-Detail page entry robustly ---
st.markdown(
    """
<style>
/* Hide links that contain the slug anywhere */
section[data-testid="stSidebar"] a[href*="a_Wohnung_Detail"] { display:none !important; }
/* Fallback for query-router */
section[data-testid="stSidebar"] a[href*="page=a%20Wohnung%20Detail"] { display:none !important; }
</style>
""",
    unsafe_allow_html=True
)


# --- Hide Wohnung-Detail page entry from the sidebar navigation (robust for both routers) ---
st.markdown(
    """
    <style>
    /* Hide by path slug (new router with path segments) */
    section[data-testid="stSidebar"] a[href$="/a_Wohnung_Detail"] { display:none !important; }
    section[data-testid="stSidebar"] a[href$="a_Wohnung_Detail"] { display:none !important; }
    /* Hide by query router (?page=...) as fallback */
    section[data-testid="stSidebar"] a[href*="page=a%20Wohnung%20Detail"] { display:none !important; }
    </style>
    """,
    unsafe_allow_html=True
)


# --- Hide detail subpage from sidebar navigation ---
st.markdown(
    """
    <style>
    /* Hide the Wohnung-Detail page link in the sidebar nav */
    section[data-testid="stSidebar"] a[href*="03a_Wohnung_Detail"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)


# Sidebar-Kopf
with st.sidebar:
    st.markdown("## 🏠 " + t("app_title"))
    st.markdown("—")
    st.caption(t("local_data_hint"))

# --- Nutzerprofil-Tabelle sicherstellen (idempotent) ---
UserProfile.__table__.create(bind=get_engine(), checkfirst=True)

# --- Begrüßung: Tageszeit + Saison + Vorname ---
def _time_greeting(hour: int) -> str:
    if 5 <= hour < 11:   return t("greet_morning")
    if 11 <= hour < 17:  return t("greet_afternoon")
    if 17 <= hour < 23:  return t("greet_evening")
    return t("greet_night")

def _season(month: int) -> tuple[str, str]:
    if month in (3, 4, 5):    return (t("spring"), "🌷")
    if month in (6, 7, 8):    return (t("summer"), "☀️")
    if month in (9, 10, 11):  return (t("autumn"), "🍂")
    return (t("winter"), "❄️")

now = dt.datetime.now()
greet = _time_greeting(now.hour)
season_label, season_emoji = _season(now.month)

with SessionCtx() as s:
    profile = s.query(UserProfile).limit(1).first()
first_name = (profile.first_name or "").strip() if profile else ""

# --- Startbildschirm (statt Dashboard) ---
st.markdown(
    f"### {greet}{', ' + first_name if first_name else ''}! {season_emoji} "
    + t("season_greeting").format(season=season_label)
)

st.write("—")
st.write("Wähle links eine Seite aus (Dashboard, Objekte, …).")