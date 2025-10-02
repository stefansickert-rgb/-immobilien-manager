import streamlit as st
import pandas as pd
import datetime as dt
from core.db import SessionCtx, Property, Unit, Lease, UnitPhoto, Radiator, Meter, MeterReading, get_engine
from core.queries import df_properties, df_units, df_leases, df_unit_photos, df_radiators, df_meters, df_meter_readings, reset_caches

st.header("Immobilien")

# kompaktere Seitenränder
st.markdown("""<style>.block-container{padding-left:1rem!important;padding-right:1rem!important}.units-table{width:100%;table-layout:auto}</style>""", unsafe_allow_html=True)

# ============ Hilfsfunktionen ============
def _bool_checkbox(val):
    if pd.isna(val):
        return ""
    return f'<input type="checkbox" {"checked" if bool(val) else ""} disabled />'

def _unit_link(row):
    uid = int(row["id"])
    label = str(row.get("unit_label", ""))
    return f'<a href="./Immobilien?unit_id={uid}" target="_self">{label}</a>'

# ============ Daten laden ============
props_df = df_properties()
units_df = df_units()
leases_df = df_leases()

# Aktive MV je Wohnung vorbereiten
def _active_leases_for_unit(uid:int):
    if leases_df is None or leases_df.empty:
        return []
    today = pd.Timestamp.today().normalize()
    sub = leases_df[leases_df['unit_id']==uid].copy()
    if sub.empty:
        return []
    sub['start_date'] = pd.to_datetime(sub['start_date'], errors='coerce').dt.normalize()
    sub['end_date'] = pd.to_datetime(sub['end_date'], errors='coerce').dt.normalize()
    active = sub[(sub['start_date']<=today) & (sub['end_date'].isna() | (sub['end_date']>=today))]
    return active.to_dict('records')


# ============ Objekt-Auswahl (oben) ============
st.subheader("Häuser / Objekte")
# Query-Param für Objekt-Vorauswahl
try:
    _q = st.query_params
    selected_prop_id_query = int((_q.get("property_id") or _q.get("prop_id") or [0])[0] or 0)
except Exception:
    selected_prop_id_query = 0
if props_df.empty:
    st.info("Noch keine Objekte erfasst.")
    selected_prop_id = 0
else:
    props_df = props_df.copy()
    props_df["Einheiten"] = props_df["id"].map(lambda pid: (units_df["property_id"] == pid).sum())
    # Auswahl
    prop_map = {f'#{row["id"]} – {row.get("label") or row.get("name") or "Objekt"} ({row["Einheiten"]} Whg)': int(row["id"]) for _, row in props_df.iterrows()}
    first_key = next(iter(prop_map)) if prop_map else None
    keys = list(prop_map.keys())
    # Index anhand Prop-ID aus Query bestimmen
    idx = 0
    if selected_prop_id_query in prop_map.values():
        try:
            idx = keys.index([k for k,v in prop_map.items() if v == selected_prop_id_query][0])
        except Exception:
            idx = 0
    selected_key = st.selectbox("Objekt auswählen", keys, index=idx if keys else 0)
    selected_prop_id = prop_map[selected_key]
    # Karte
    sel = props_df.loc[props_df["id"] == selected_prop_id].iloc[0].to_dict()
    with st.container(border=True):
        st.markdown(
            f"""**Adresse:** {sel.get('address','-')}  
**Notiz:** {sel.get('notes','-')}  
**Einheiten:** {sel.get('Einheiten',0)}"""
        )

# ============ Wohnungen im gewählten Objekt (direkt darunter) ============
st.subheader("Wohnungen im gewählten Objekt")
_df = units_df.copy()
if selected_prop_id:
    _df = _df[_df["property_id"] == selected_prop_id]

if _df.empty:
    st.info("Keine Wohnungen im gewählten Objekt.")
else:
    _df = _df.copy()
    _df["unit_label"] = _df.apply(_unit_link, axis=1)
    # Zusätzliche Spalten: Mieter (aktiv) und Kaltmiete laut MV
    def _tenants_str(uid):
        recs = _active_leases_for_unit(int(uid))
        items = []
        for r in recs:
            name = r.get('tenant_name')
            tid = r.get('tenant_id')
            if name and tid:
                items.append(f'<a target="_self" href="/Mieter?tenant_id={int(tid)}#tenant">{name}</a>')
            elif name:
                items.append(name)
        return ", ".join(items) if items else "—"
    def _rent_cold(uid):
        recs = _active_leases_for_unit(int(uid))
        if not recs:
            return "—"
        recs = sorted(recs, key=lambda r: pd.to_datetime(r.get('start_date')), reverse=True)
        rc = recs[0].get('rent_cold')
        try:
            return f"{float(rc):.2f}"
        except Exception:
            return str(rc) if rc is not None else "—"
    _df['Mieter'] = _df['id'].map(_tenants_str)
    _df['Kaltmiete lt. MV'] = _df['id'].map(_rent_cold)
    for col in [c for c in _df.columns if _df[c].dtype == bool or c in ("is_rented","balcony","cellar","storage_room","garage","parking_spot","owned_by_me")]:
        _df[col] = _df[col].map(_bool_checkbox)

    rename_map = {
        "id":"ID","property_id":"Objekt","unit_label":"Wohnungsbezeichnung","rooms":"Zimmer",
        "living_area":"Wohnfläche (m²)","rent_cold":"aktuelle Kaltmiete (€)","is_rented":"vermietet","Mieter":"Mieter","Kaltmiete lt. MV":"Kaltmiete lt. MV",
        "balcony":"Balkon","cellar":"Keller","storage_room":"Abstellraum","garage":"Garage",
        "parking_spot":"PKW-Stellplatz","owned_by_me":"In meinem Eigentum"
    }
    keep = [c for c in ["id","property_id","unit_label","rooms","living_area","rent_cold","is_rented","Mieter","Kaltmiete lt. MV","balcony","cellar","storage_room","garage","parking_spot","owned_by_me"] if c in _df.columns]
    _df = _df[keep].rename(columns=rename_map)
    st.markdown(_df.to_html(classes="units-table", escape=False, index=False, border=0), unsafe_allow_html=True)

st.markdown('---')

# ============ Inline-Details (Tabs) ============
try:
    q = st.query_params
    selected_unit_id = int((q.get("unit_id") or [None])[0] or 0)
except Exception:
    selected_unit_id = 0

if selected_unit_id:
    st.subheader("Wohnung – Details")
    if st.button("← Zurück zur objektweiten Liste", key="back_to_list_units"):
        try:
            try: st.query_params.pop("unit_id", None)
            except Exception: pass
            try: st.experimental_set_query_params()
            except Exception: pass
        except Exception: pass
        st.rerun()

    with SessionCtx() as s:
        unit = s.get(Unit, selected_unit_id)

    if not unit:
        st.error(f"Wohnung #{selected_unit_id} nicht gefunden.")
    else:
        st.markdown(f"#### #{unit.id} – {unit.unit_label or ''}")

        tab_fotos, tab_notizen, tab_radiatoren, tab_zaehler = st.tabs(["Fotos", "Notizen", "Heizkörper", "Zähler"])

        with tab_fotos:
            photos_df = df_unit_photos(selected_unit_id)
            if photos_df is not None and not photos_df.empty:
                if 'position' in photos_df.columns and photos_df['position'].notna().any():
                    photos_df = photos_df.sort_values(['position','uploaded_at','id'], ascending=[True, False, False], na_position='last')
                else:
                    photos_df = photos_df.sort_values(['uploaded_at','id'], ascending=[False, False])
            count_existing = 0 if (photos_df is None or photos_df.empty) else len(photos_df)

            c_up, c_info = st.columns([3,2])
            with c_up:
                uploaded = st.file_uploader("Bis zu 10 Fotos hinzufügen", type=["png","jpg","jpeg","webp"], accept_multiple_files=True, key="unit_photos_inline")
                if uploaded:
                    to_add = uploaded[: max(0, 10 - count_existing)]
                    if len(uploaded) > len(to_add):
                        st.info(f"Es sind bereits {count_existing}/10 Bilder vorhanden – füge {len(to_add)} neue hinzu.")
                    prev_cols = st.columns(5)
                    for i, file in enumerate(to_add):
                        with prev_cols[i % 5]:
                            st.image(file, caption=file.name, use_column_width=True)
                    if st.button("Fotos speichern", key="save_photos_inline"):
                        with SessionCtx() as s2:
                            # max Position ermitteln
                            try:
                                from sqlalchemy import select, func as _func
                                qmax = s2.execute(select(_func.max(UnitPhoto.position)).where(UnitPhoto.unit_id==selected_unit_id)).scalar()
                                max_pos = int(qmax or 0)
                            except Exception:
                                max_pos = 0
                            for idx, file in enumerate(to_add, start=1):
                                img_bytes = file.read()
                                s2.add(UnitPhoto(unit_id=selected_unit_id, filename=file.name, image=img_bytes, uploaded_at=dt.date.today(), position=max_pos+idx))
                            s2.commit()
                        reset_caches(); st.success("Fotos gespeichert."); st.rerun()
            with c_info:
                st.caption(f"Aktuell gespeichert: **{count_existing}/10**")

            photos_df = df_unit_photos(selected_unit_id)
            if photos_df is None or photos_df.empty:
                st.info("Noch keine Fotos vorhanden.")
            else:
                st.markdown("**Fotos verwalten**")
                del_ids = []; order_updates = {}
                grid_cols = st.columns(5)
                for i, (_, row) in enumerate(photos_df.iterrows()):
                    with grid_cols[i % 5]:
                        st.image(row["image"], caption=row.get("filename") or f"Foto #{row['id']}", use_column_width=True)
                        if st.checkbox("Löschen", key=f"ph_del_{row['id']}"):
                            del_ids.append(int(row['id']))
                        current_pos = int(row.get('position') or (i+1))
                        new_pos = st.number_input("Reihenfolge", min_value=1, max_value=len(photos_df), value=current_pos, step=1, key=f"ph_pos_{row['id']}")
                        order_updates[int(row['id'])] = int(new_pos)

                c_act1, c_act2 = st.columns([1,1])
                with c_act1:
                    if st.button("Markierte löschen", key="bulk_delete_photos"):
                        if del_ids:
                            with SessionCtx() as sdel:
                                for pid in del_ids:
                                    p = sdel.get(UnitPhoto, pid)
                                    if p: sdel.delete(p)
                                sdel.commit()
                            reset_caches(); st.success(f"{len(del_ids)} Foto(s) gelöscht."); st.rerun()
                        else:
                            st.info("Keine Fotos markiert.")
                with c_act2:
                    if st.button("Reihenfolge speichern", key="save_order_photos"):
                        with SessionCtx() as sset:
                            for pid, pos in order_updates.items():
                                p = sset.get(UnitPhoto, pid)
                                if p:
                                    p.position = pos
                            sset.commit()
                        reset_caches(); st.success("Reihenfolge gespeichert."); st.rerun()

        with tab_notizen:
                st.markdown("### Notizen")
                with SessionCtx() as s4:
                    u4 = s4.get(Unit, selected_unit_id)
                    current = getattr(u4, "notes", "") or ""
                    new = st.text_area("Notizen zur Wohnung", value=current, height=120, key="notes_inline")
                    if st.button("Notizen speichern", key="save_notes_inline"):
                        try:
                            setattr(u4, "notes", new)
                            s4.add(u4); s4.commit()
                            reset_caches(); st.success("Gespeichert.")
                        except Exception as e:
                            st.error(f"Konnte Notizen nicht speichern: {e}")

        with tab_radiatoren:
            st.markdown("### Heizkörper")
            r_df = df_radiators(selected_unit_id)
            if r_df is not None and not r_df.empty:
                st.dataframe(r_df.rename(columns={"label":"Bezeichnung","notes":"Notiz"}), use_container_width=True, hide_index=True)
            else:
                st.info("Noch keine Heizkörper erfasst.")
            with st.form("add_radiator_inline"):
                c1, c2 = st.columns([1,2])
                with c1:
                    label = st.text_input("Bezeichnung*", placeholder="z. B. WZ links", key="rad_label_inline")
                with c2:
                    notes = st.text_input("Notiz", key="rad_notes_inline")
                if st.form_submit_button("Heizkörper hinzufügen"):
                    if not (label or "").strip():
                        st.error("Bitte Bezeichnung angeben.")
                    else:
                        with SessionCtx() as s5:
                            s5.add(Radiator(unit_id=selected_unit_id, label=label.strip(), notes=notes or None)); s5.commit()
                        reset_caches(); st.success("Hinzugefügt."); st.rerun()

        with tab_zaehler:
            st.markdown("### Zähler & Stände")
            m_df = df_meters(selected_unit_id)
            if m_df is None or m_df.empty:
                st.info("Noch keine Zähler angelegt.")
            else:
                st.dataframe(m_df.rename(columns={"meter_type":"Typ","location":"Ort","notes":"Notiz"}), use_container_width=True, hide_index=True)
                meter_map = {f"#{row['id']} – {row['meter_type']}": int(row['id']) for _, row in m_df.iterrows()}
                meter_label = st.selectbox("Zähler auswählen", list(meter_map.keys()), key="meter_select_inline")
                meter_id = meter_map[meter_label]

                rd_df = df_meter_readings(meter_id)
                if rd_df is not None and not rd_df.empty:
                    st.dataframe(rd_df.rename(columns={"read_date":"Datum","value":"Stand"}).sort_values("read_date", ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Noch keine Zählerstände erfasst.")

                with st.form("reading_inline"):
                    c1, c2 = st.columns(2)
                    with c1:
                        rd = st.date_input("Datum*", value=dt.date.today())
                    with c2:
                        val = st.number_input("Stand*", min_value=0.0, step=1.0, format="%f")
                    if st.form_submit_button("Zählerstand hinzufügen"):
                        with SessionCtx() as s6:
                            s6.add(MeterReading(meter_id=meter_id, read_date=rd, value=val)); s6.commit()
                        reset_caches(); st.success("Hinzugefügt."); st.rerun()