# --- Build Version: v5.1.2 | generated 2025-10-03 20:29:17 ---
import datetime as dt
import streamlit as st
from core.db import init_db, SessionCtx, UserProfile, get_engine
from core.i18n import t

# DB initialisieren (Schema-Version an deine aktuelle anpassen, z.B. 3)
init_db(schema_version=8)

# Seiten-Setup
st.set_page_config(page_title=t("app_title"), page_icon="🏠", layout="wide")

# ----------------------- AUTHENTICATION GATE (robust) -----------------------
import os, streamlit as st
import streamlit_authenticator as stauth
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

name, auth_status, username = _auth.login("Login", "main")
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
