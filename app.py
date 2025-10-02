import datetime as dt
import streamlit as st
from core.db import init_db, SessionCtx, UserProfile, get_engine
from core.i18n import t

# DB initialisieren (Schema-Version an deine aktuelle anpassen, z.B. 3)
init_db(schema_version=8)

# Seiten-Setup
st.set_page_config(page_title=t("app_title"), page_icon="🏠", layout="wide")

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
