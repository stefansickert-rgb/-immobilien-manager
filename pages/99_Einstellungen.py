import streamlit as st
import datetime as dt
from sqlalchemy import select, func
from core.db import SessionCtx, Property, Unit, Tenant, Lease, Payment, MaintenanceTask
from core.queries import reset_caches
from core.i18n import t, set_lang, get_lang, LANGS

st.header(t("settings"))

# Sprachwahl (persistiert in st.session_state["lang"])
human = {"de": t("german"), "en": t("english"), "fr": t("french"), "es": t("spanish")}
current = get_lang()
labels = [human[c] for c in LANGS]
idx = LANGS.index(current)
choice = st.selectbox(t("language"), labels, index=idx)

selected_code = LANGS[labels.index(choice)]
if selected_code != current:
    set_lang(selected_code)
    st.toast(t("language_changed"))
    try:
        st.rerun()
    except Exception:
        if hasattr(st, "experimental_rerun"):
            st.rerun()

st.caption("—")

# (Rest der Seite kann bleiben – hier nur Beispiel mit Demo-Daten / Reset)
st.subheader("Demo-Daten anlegen (optional)")
if st.button("Demo-Daten einfügen"):
    with SessionCtx() as s:
        has_any = s.execute(select(func.count(Property.id))).scalar_one()
        if not has_any:
            p = Property(name="Musterstraße 1", address="Musterstraße 1", postal_code="01833",
                         city="Beispielstadt", purchase_price=300000, size_sqm=260)
            s.add(p); s.flush()
            u1 = Unit(property_id=p.id, unit_label="Whg 1", rooms=3.0, living_area_sqm=70.0,
                      rent_cold_current=650, is_rented=True)
            u2 = Unit(property_id=p.id, unit_label="Whg 2", rooms=2.0, living_area_sqm=50.0,
                      rent_cold_current=520, is_rented=False)
            s.add_all([u1, u2])
            t1 = Tenant(full_name="Max Mustermann", email="max@example.com"); s.add(t1); s.flush()
            l1 = Lease(unit_id=u1.id, tenant_id=t1.id, start_date=dt.date.today().replace(year=dt.date.today().year-1),
                       rent_cold=650, rent_warm=800, deposit=1300)
            s.add(l1); s.flush()
            s.add(Payment(lease_id=l1.id, pay_date=dt.date.today(), amount=650, category="Miete", note="September"))
            s.add(MaintenanceTask(property_id=p.id, title="Haustür streichen", status="offen", cost_estimate=200))
            s.commit()
        else:
            st.info("Es existieren bereits Daten – Demo nicht eingefügt.")
    reset_caches(); st.success("Demo-Daten eingefügt.")

st.subheader("Datenbank zurücksetzen")
st.warning("ACHTUNG: Löscht alle Daten unwiderruflich (Datei data.db bleibt, aber Tabellen werden geleert).")
if st.button("Alles löschen"):
    with SessionCtx() as s:
        s.query(Payment).delete(); s.query(Lease).delete(); s.query(Unit).delete()
        s.query(MaintenanceTask).delete(); s.query(Tenant).delete(); s.query(Property).delete(); s.commit()
    reset_caches(); st.success("Alle Tabellen geleert.")
