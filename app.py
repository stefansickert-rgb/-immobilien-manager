# --- Build Version: v5.1.6 | generated 2025-10-03 21:20:38 ---
import datetime as dt
import streamlit as st
from core.db import init_db, SessionCtx, UserProfile, get_engine
from core.i18n import t

# DB initialisieren (Schema-Version an deine aktuelle anpassen, z.B. 3)
init_db(schema_version=8)

# Seiten-Setup
st.set_page_config(page_title=t("app_title"), page_icon="🏠", layout="wide")

# Sidebar-Navigation verstecken, solange nicht eingeloggt
def _hide_nav_when_logged_out():
    import streamlit as st
    if not st.session_state.get("auth"):
        st.markdown("""
            <style>
              [data-testid="stSidebarNav"] { display: none !important; }
              [data-testid="stSidebar"] [data-testid="stSidebarNav"] ~ div { display: none !important; }
            </style>
        """, unsafe_allow_html=True)

_hide_nav_when_logged_out()

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

def _do_register(u, mail, name, p1, p2):
    if not u or not p1:
        return "Bitte Benutzername und Passwort ausfüllen."
    if p1 != p2:
        return "Passwörter stimmen nicht überein."
    with SessionCtx() as s:
        exists = s.query(User).filter(User.username == u).one_or_none()
        if exists:
            return "Benutzername ist bereits vergeben."
        s.add(User(username=u, email=mail or None, full_name=name or u, password_hash=hash_password(p1), role="viewer", is_active=True))
        s.commit()
    return None

if not st.session_state.get("auth"):
    st.subheader("Willkommen – bitte anmelden oder registrieren")
    tab_login, tab_register = st.tabs(["Anmelden", "Registrieren"])
    with tab_login:
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
    with tab_register:
        with st.form("register_form"):
            u2 = st.text_input("Benutzername")
            name2 = st.text_input("Vollständiger Name", value="")
            mail2 = st.text_input("E-Mail (optional)", value="")
            c1, c2 = st.columns(2)
            with c1:
                p1 = st.text_input("Passwort", type="password")
            with c2:
                p2 = st.text_input("Passwort wiederholen", type="password")
            okr = st.form_submit_button("Registrieren")
        if okr:
            err = _do_register(u2.strip(), mail2.strip(), name2.strip(), p1, p2)
            if err:
                st.error(err)
            else:
                st.success("Registrierung erfolgreich – bitte jetzt anmelden.")
    st.stop()

with st.sidebar:
    st.caption(f"Eingeloggt als: **{st.session_state['auth']['username']}**")
    if st.button("Logout"):
        st.session_state.pop("auth", None)
        st.rerun()
# -----------------------------------------------------------------

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