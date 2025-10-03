from core.auth import require_login; _authctx = require_login()
import re
import streamlit as st
from sqlalchemy import select
from core.db import SessionCtx, UserProfile, get_engine
from core.i18n import t

st.header(t("user_account"))
st.subheader(t("edit_profile"))

# --- Tabelle/Spalte sicherstellen (idempotent) ---
eng = get_engine()
# Tabelle anlegen, falls sie fehlt
UserProfile.__table__.create(bind=eng, checkfirst=True)
# Spalte 'avatar' nachziehen, falls alte DB
with eng.connect() as conn:
    cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(user_profile)").fetchall()]
    if "avatar" not in cols:
        conn.exec_driver_sql("ALTER TABLE user_profile ADD COLUMN avatar BLOB")

# 1) Profil laden oder anlegen
with SessionCtx() as s:
    profile = s.execute(select(UserProfile).limit(1)).scalars().first()
    if not profile:
        profile = UserProfile(first_name=None, last_name=None, email=None, avatar=None)
        s.add(profile); s.commit(); s.refresh(profile)


# --- Avatar-Anzeige / Upload ---
st.markdown("### " + t("avatar"))

col_preview, col_actions = st.columns([1, 2])
with col_preview:
    if profile.avatar:
        st.image(profile.avatar, caption="", use_container_width=False)
    else:
        st.caption("—")

with col_actions:
    # Upload (separates Formular, damit man Bild speichern kann ohne Textfelder zu überschreiben)
    with st.form("avatar_form"):
        uploaded = st.file_uploader(t("upload_photo"), type=["png", "jpg", "jpeg"])
        save_avatar = st.form_submit_button(t("save"))
    if save_avatar:
        if uploaded:
            data = uploaded.read()
            # Minimaler Check auf Bild-Signatur (optional)
            if len(data) < 10:
                st.error(t("invalid_image"))
            else:
                with SessionCtx() as s:
                    p = s.get(UserProfile, profile.id)
                    p.avatar = data
                    s.add(p); s.commit()
                st.success(t("photo_saved"))
                st.rerun()
        else:
            st.info(t("invalid_image"))

    # Entfernen
    if profile.avatar and st.button(t("remove_photo"), type="secondary"):
        with SessionCtx() as s:
            p = s.get(UserProfile, profile.id)
            p.avatar = None
            s.add(p); s.commit()
        st.success(t("photo_removed"))
        st.rerun()

st.divider()

# --- Profildaten-Form ---
with st.form("user_profile_form"):
    c1, c2 = st.columns(2)
    with c1:
        first_name = st.text_input(t("first_name"), value=profile.first_name or "")
        email = st.text_input(t("email"), value=profile.email or "")
    with c2:
        last_name = st.text_input(t("last_name"), value=profile.last_name or "")
    submitted = st.form_submit_button(t("save"))

if submitted:
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        st.error(t("email") + " – invalid format.")
    else:
        with SessionCtx() as s:
            p = s.get(UserProfile, profile.id)
            p.first_name = first_name.strip() or None
            p.last_name  = last_name.strip() or None
            p.email      = email.strip() or None
            s.add(p); s.commit()
        st.success(t("profile_saved"))
        st.rerun()
