
import streamlit as st
import pandas as pd
import numpy as np
import io
from core.i18n import t
from core.db import get_engine
from sqlalchemy import text

st.set_page_config(layout="wide")
st.header(t("operating_costs", "Betriebskosten"))

engine = get_engine()

# -----------------------------
# Helpers
# -----------------------------
def find_logo_path():
    for p in ["assets/logo.png", "logo.png", "assets/logo.jpg", "logo.jpg"]:
        try:
            Path(p).stat()
            return p
        except Exception:
            pass
    return None

def df_properties():
    return pd.read_sql("SELECT id, name FROM properties ORDER BY id", engine)

def df_units(prop_id: int):
    sql = text("SELECT id, unit_label, living_area_sqm FROM units WHERE property_id = :pid ORDER BY id")
    return pd.read_sql(sql, engine, params={"pid": prop_id})

def df_categories():
    return pd.read_sql("SELECT code, name, name_en, allocation_method, is_heating FROM cost_categories ORDER BY code", engine)

def df_costs(prop_id: int | None = None):
    if prop_id:
        return pd.read_sql(text("SELECT * FROM operating_costs WHERE property_id = :pid ORDER BY date DESC, id DESC"), engine, params={"pid": prop_id})
    return pd.read_sql("SELECT * FROM operating_costs ORDER BY date DESC, id DESC", engine)

def df_settings(prop_id: int):
    rows = pd.read_sql(text("SELECT * FROM property_settings WHERE property_id = :pid"), engine, params={"pid": prop_id})
    if rows.empty:
        return {"heat_ratio_consumption": 70, "persons_default": 2, "water_allocation_fallback": "PERSONS"}
    return rows.iloc[0].to_dict()

def df_unit_persons(prop_id: int, year: int):
    sql = text("SELECT unit_id, persons FROM unit_persons WHERE property_id = :pid AND year = :yr")
    return pd.read_sql(sql, engine, params={"pid": prop_id, "yr": year}).set_index("unit_id") if year else pd.DataFrame()

def consumption_by_unit(prop_id: int, year: int, kind: str):
    """Compute consumption per unit for given property/year.
    kind: 'water' or 'heat' (match meters.type case-insensitively).
    Uses difference of readings around period.
    """
    meters = pd.read_sql(
        text("""
        SELECT m.id AS meter_id, m.unit_id, LOWER(m.type) AS mtype
        FROM meters m
        JOIN units u ON u.id = m.unit_id
        WHERE u.property_id = :pid
        """),
        engine, params={"pid": prop_id}
    )
    if meters.empty:
        return {}
    def is_kind(s: str) -> bool:
        s = s or ""
        if kind == 'water':
            return any(k in s for k in ['water','wasser','h2o'])
        return any(k in s for k in ['heat','heiz','wärme','warm','therm'])
    meters = meters[meters['mtype'].apply(is_kind)]
    if meters.empty:
        return {}

    start = pd.Timestamp(year=year, month=1, day=1)
    end = pd.Timestamp(year=year, month=12, day=31, hour=23, minute=59, second=59)

    out: dict[int, float] = {}
    for r in meters.itertuples(index=False):
        mid = int(r.meter_id); uid = int(r.unit_id)
        rd = pd.read_sql(text("SELECT read_date, value FROM meter_readings WHERE meter_id = :mid ORDER BY read_date"), engine, params={"mid": mid})
        if rd.empty:
            continue
        rd['read_date'] = pd.to_datetime(rd['read_date'], errors='coerce')
        # Value at (or before) start
        before_start = rd[rd['read_date'] <= start]
        v0 = float(before_start.iloc[-1]['value']) if not before_start.empty else float(rd.iloc[0]['value'])
        # Value at (or before) end
        before_end = rd[rd['read_date'] <= end]
        v1 = float(before_end.iloc[-1]['value']) if not before_end.empty else float(rd.iloc[-1]['value'])
        cons = max(0.0, v1 - v0)
        out[uid] = out.get(uid, 0.0) + cons
    return out

# -----------------------------
# Page scaffold
# -----------------------------
props = df_properties()
if props.empty:
    st.info(t("no_properties", "Noch keine Objekte vorhanden."))
    st.stop()

prop_name_map = dict(zip(props["name"], props["id"]))
prop_choice = st.selectbox(t("select_property", "Objekt wählen"), list(prop_name_map.keys()))
prop_id = prop_name_map[prop_choice]

tab1, tab2, tab3 = st.tabs([t("oc_tab_entry", "Kosten erfassen"), t("oc_tab_keys", "Umlageschlüssel"), t("oc_tab_statement", "Abrechnung")])

# -----------------------------
# Tab 1: Kosten erfassen
# -----------------------------
with tab1:
    st.subheader(t("oc_entry", "Kosten erfassen"))
    colf = st.columns(3)
    date = colf[0].date_input(t("date", "Datum"), pd.Timestamp.today())
    cat_df = df_categories()
    cat_label = colf[1].selectbox(t("category", "Kategorie"), cat_df["code"] + " — " + cat_df["name"])
    amount = colf[2].number_input(t("amount", "Betrag (€)"), min_value=0.0, step=10.0, format="%.2f")

    colg = st.columns(4)
    period_start = colg[0].date_input("Periodenbeginn", pd.Timestamp(pd.Timestamp.today().year,1,1))
    period_end = colg[1].date_input("Periodenende", pd.Timestamp(pd.Timestamp.today().year,12,31))
    vat_rate = colg[2].number_input("USt-Satz (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, format="%.0f")
    unit_df = df_units(prop_id)
    unit_map = {f"{r.unit_label} (#{int(r.id)})": int(r.id) for r in unit_df.itertuples(index=False)} if not unit_df.empty else {}
    unit_choice = colg[3].selectbox(t("unit_optional","Wohnung (optional)"), ["—"] + list(unit_map.keys()))

    colh = st.columns(3)
    supplier = colh[0].text_input(t("supplier","Lieferant"))
    invoice = colh[1].text_input(t("invoice_no","Rechnungsnr."))
    description = colh[2].text_input(t("description","Beschreibung"))

    if st.button(t("save","Speichern"), type="primary"):
        code = cat_label.split(" — ")[0]
        unit_id = unit_map.get(unit_choice) if unit_choice in unit_map else None
        with engine.begin() as con:
            con.exec_driver_sql(
                "INSERT INTO operating_costs (property_id, unit_id, date, period_start, period_end, category_code, amount_gross, vat_rate, supplier, invoice_no, description) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (prop_id, unit_id, pd.to_datetime(date).date(), pd.to_datetime(period_start).date(), pd.to_datetime(period_end).date(), code, float(amount), float(vat_rate or 0.0), supplier or None, invoice or None, description or None)
            )
        st.success(t("saved","Gespeichert."))
        st.rerun()

    st.markdown("#### " + t("oc_list","Erfasste Kosten"))
    costs = df_costs(prop_id)
    if not costs.empty:
        st.dataframe(costs, use_container_width=True, hide_index=True)
    else:
        st.caption(t("not_available","Noch keine Daten vorhanden."))

# -----------------------------
# Tab 2: Umlageschlüssel
# -----------------------------
with tab2:
    st.subheader(t("oc_keys","Umlageschlüssel & Parameter"))
    settings = df_settings(prop_id)
    c = st.columns(3)
    heat_ratio = c[0].slider("Heizkosten: Verbrauchsanteil (%)", 50, 70, int(settings.get("heat_ratio_consumption",70)))
    persons_default = c[1].number_input("Personen (Fallback)", min_value=0, value=int(settings.get("persons_default",2)))
    water_fb = c[2].selectbox("Fallback Wasser", ["PERSONS","UNITS"], index=0 if settings.get("water_allocation_fallback","PERSONS")=="PERSONS" else 1)

    if st.button(t("save","Speichern"), key="save_settings"):
        with engine.begin() as con:
            con.exec_driver_sql("INSERT INTO property_settings (property_id, heat_ratio_consumption, persons_default, water_allocation_fallback) VALUES (?,?,?,?) ON CONFLICT(property_id) DO UPDATE SET heat_ratio_consumption=excluded.heat_ratio_consumption, persons_default=excluded.persons_default, water_allocation_fallback=excluded.water_allocation_fallback", (prop_id, int(heat_ratio), int(persons_default), water_fb))
        st.success(t("changes_saved","Gespeichert."))

    st.markdown("#### " + t("oc_persons","Personen je Wohnung (Jahr)"))
    years = list(range(pd.Timestamp.today().year-2, pd.Timestamp.today().year+1))
    y2 = st.selectbox(t("year","Jahr"), years, index=2, key="persons_year")
    units_df2 = df_units(prop_id)
    if not units_df2.empty:
        persons_df = df_unit_persons(prop_id, y2).reindex(units_df2["id"]).fillna(0).astype(int)
        edit_df = pd.DataFrame({"unit_id": units_df2["id"].values, "Wohnung": units_df2["unit_label"].values, "Personen": persons_df["persons"].values})
        edited = st.data_editor(edit_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button(t("save","Speichern"), key="save_persons"):
            with engine.begin() as con:
                con.exec_driver_sql("DELETE FROM unit_persons WHERE property_id=? AND year=?", (prop_id, int(y2)))
                for r in edited.itertuples(index=False):
                    con.exec_driver_sql("INSERT INTO unit_persons (property_id, unit_id, year, persons) VALUES (?,?,?,?)", (prop_id, int(r.unit_id), int(y2), int(r.Personen)))
            st.success(t("changes_saved","Gespeichert."))

# -----------------------------
# Tab 3: Abrechnung
# -----------------------------
with tab3:
    st.subheader(t("oc_statement","Abrechnungsvorschau"))
    y = st.selectbox(t("year","Jahr"), list(range(pd.Timestamp.today().year-2, pd.Timestamp.today().year+1)), index=2, key="year_stmt")

    units_df = df_units(prop_id)
    if units_df.empty:
        st.info(t("no_units","Noch keine Wohnungen vorhanden."))
        st.stop()

    total_area = units_df["living_area_sqm"].fillna(0).sum()
    up = df_unit_persons(prop_id, int(y))
    persons_map = up["persons"].to_dict() if not up.empty else {}
    settings = df_settings(prop_id)
    persons_sum = sum(persons_map.values()) or len(units_df) * settings.get("persons_default",2)

    # Kosten im Jahr
    q = text("""
        SELECT id, category_code, unit_id, amount_gross, COALESCE(vat_rate,0) AS vat_rate
        FROM operating_costs
        WHERE property_id = :pid AND strftime('%Y', date) = :yr
        """ )
    costs = pd.read_sql(q, engine, params={"pid": prop_id, "yr": str(y)})

    cats = df_categories().set_index("code")
    result = pd.DataFrame(index=units_df["id"], columns=["sum"], data=0.0)

    def add_amount_for_units(df, amount_map):
        for uid, val in amount_map.items():
            df.loc[uid, "sum"] = df.loc[uid, "sum"] + float(val)

    # Aggregierte Verteilung für Vorschau
    for rowc in costs.itertuples(index=False):
        code = rowc.category_code
        alloc = cats.loc[code, "allocation_method"] if code in cats.index else "UNITS"
        amt = float(rowc.amount_gross)
        if rowc.unit_id:
            add_amount_for_units(result, {int(rowc.unit_id): amt})
            continue
        shares = {}
        if alloc == "AREA" and total_area > 0:
            for r in units_df.itertuples(index=False):
                shares[int(r.id)] = (float(r.living_area_sqm or 0)/total_area) * amt
        elif alloc == "UNITS":
            per = amt / len(units_df); shares = {int(r.id): per for r in units_df.itertuples(index=False)}
        elif alloc == "PERSONS":
            total_persons = persons_sum or len(units_df)
            for r in units_df.itertuples(index=False):
                p = persons_map.get(int(r.id), settings.get("persons_default",2))
                shares[int(r.id)] = (p/total_persons) * amt
        elif alloc == "WATER_M3":
            water_cons = consumption_by_unit(prop_id, int(y), 'water')
            totalw = sum(water_cons.values())
            if totalw > 0:
                for r in units_df.itertuples(index=False):
                    shares[int(r.id)] = (float(water_cons.get(int(r.id),0.0))/totalw) * amt
            else:
                fb = settings.get("water_allocation_fallback","PERSONS")
                if fb == "UNITS":
                    per = amt / len(units_df); shares = {int(r.id): per for r in units_df.itertuples(index=False)}
                else:
                    total_persons = persons_sum or len(units_df)
                    for r in units_df.itertuples(index=False):
                        p = persons_map.get(int(r.id), settings.get("persons_default",2))
                        shares[int(r.id)] = (p/total_persons) * amt
        elif alloc == "HEAT_SPLIT_70_30":
            ratio = int(settings.get("heat_ratio_consumption",70))
            cons_ratio = ratio/100.0; base_ratio = 1.0 - cons_ratio
            heat_cons = consumption_by_unit(prop_id, int(y), 'heat')
            totalh = sum(heat_cons.values())
            for r in units_df.itertuples(index=False):
                area_share = (float(r.living_area_sqm or 0)/total_area) if total_area>0 else 1.0/len(units_df)
                cons_share = (float(heat_cons.get(int(r.id),0.0))/totalh) if totalh>0 else area_share
                shares[int(r.id)] = amt * (cons_ratio*cons_share + base_ratio*area_share)
        else:
            per = amt / len(units_df); shares = {int(r.id): per for r in units_df.itertuples(index=False)}
        add_amount_for_units(result, shares)

    out = units_df[["id","unit_label","living_area_sqm"]].copy()
    out = out.merge(result, left_on="id", right_index=True, how="left")
    out = out.rename(columns={"unit_label": t("unit_label","Wohnung"), "living_area_sqm": t("living_area_sqm","Wohnfläche (m²)"), "sum": t("total","Summe (€)")})
    out[t("total","Summe (€)")] = out[t("total","Summe (€)")].fillna(0).round(2)
    st.dataframe(out, use_container_width=True, hide_index=True)

    # -----------------------------
    # Einzelabrechnung je Mietpartei
    # -----------------------------
    st.markdown("#### " + t("oc_statement_single", "Abrechnung für eine Mietpartei"))

    q_lease = text("""
        SELECT l.id AS lease_id, u.id AS unit_id, u.unit_label, COALESCE(t.full_name,'') AS tenant
        FROM leases l
        JOIN units u ON u.id = l.unit_id
        LEFT JOIN tenants t ON t.id = l.tenant_id
        WHERE u.property_id = :pid
          AND (strftime('%Y', l.start_date) <= :yr)
          AND (l.end_date IS NULL OR strftime('%Y', l.end_date) >= :yr)
        ORDER BY u.id
        """ )
    leases_df = pd.read_sql(q_lease, engine, params={"pid": prop_id, "yr": str(y)})
    if leases_df.empty:
        st.info(t("no_leases","Keine Mietverhältnisse im gewählten Jahr."))
    else:
        leases_df["label"] = leases_df.apply(lambda r: f"{r['unit_label']} — {r['tenant'] or 'o.V.'} (Lease #{int(r['lease_id'])})", axis=1)
        choice = st.selectbox(t("choose_party","Mietpartei wählen"), leases_df["label"].tolist())
        sel = leases_df[leases_df["label"]==choice].iloc[0]
        my_unit = int(sel["unit_id"])

        # Detailierte Verteilung je Originalrechnung inkl. USt
        base_costs = costs  # already filtered property/year
        detail_rows = []
        for rpos in base_costs.itertuples(index=False):
            code = rpos.category_code
            alloc = cats.loc[code, "allocation_method"] if code in cats.index else "UNITS"
            amt = float(rpos.amount_gross)
            vat_rate = float(getattr(rpos, 'vat_rate', 0.0) or 0.0)
            if rpos.unit_id:
                detail_rows.append((int(rpos.unit_id), code, amt, vat_rate))
                continue
            shares = {}
            if alloc == "AREA" and total_area > 0:
                for u in units_df.itertuples(index=False):
                    shares[int(u.id)] = (float(u.living_area_sqm or 0)/total_area) * amt
            elif alloc == "UNITS":
                per = amt / len(units_df); shares = {int(u.id): per for u in units_df.itertuples(index=False)}
            elif alloc == "PERSONS":
                total_persons = persons_sum or len(units_df)
                for u in units_df.itertuples(index=False):
                    p = persons_map.get(int(u.id), settings.get("persons_default",2))
                    shares[int(u.id)] = (p/total_persons) * amt
            elif alloc == "WATER_M3":
                water_cons = consumption_by_unit(prop_id, int(y), 'water')
                totalw = sum(water_cons.values())
                if totalw > 0:
                    for u in units_df.itertuples(index=False):
                        shares[int(u.id)] = (float(water_cons.get(int(u.id),0.0))/totalw) * amt
                else:
                    fb = settings.get("water_allocation_fallback","PERSONS")
                    if fb == "UNITS":
                        per = amt / len(units_df); shares = {int(u.id): per for u in units_df.itertuples(index=False)}
                    else:
                        total_persons = persons_sum or len(units_df)
                        for u in units_df.itertuples(index=False):
                            p = persons_map.get(int(u.id), settings.get("persons_default",2))
                            shares[int(u.id)] = (p/total_persons) * amt
            elif alloc == "HEAT_SPLIT_70_30":
                ratio = int(settings.get("heat_ratio_consumption",70))
                cons_ratio = ratio/100.0; base_ratio = 1.0 - cons_ratio
                heat_cons = consumption_by_unit(prop_id, int(y), 'heat')
                totalh = sum(heat_cons.values())
                for u in units_df.itertuples(index=False):
                    area_share = (float(u.living_area_sqm or 0)/total_area) if total_area>0 else 1.0/len(units_df)
                    cons_share = (float(heat_cons.get(int(u.id),0.0))/totalh) if totalh>0 else area_share
                    shares[int(u.id)] = amt * (cons_ratio*cons_share + base_ratio*area_share)
            else:
                per = amt / len(units_df); shares = {int(u.id): per for u in units_df.itertuples(index=False)}
            for uid, val in shares.items():
                detail_rows.append((uid, code, float(val), vat_rate))

        detail_full = pd.DataFrame(detail_rows, columns=["unit_id","category","gross","vat_rate"])
        my_details = detail_full[detail_full["unit_id"]==my_unit].copy()
        my_details["net"] = my_details.apply(lambda r: (r["gross"]/(1+r["vat_rate"]/100.0) if r["vat_rate"] else r["gross"]), axis=1)
        my_details["vat_amount"] = my_details["gross"] - my_details["net"]

        # Heizung vs NK (nutze is_heating-Flag)
        cat_meta = cats[["is_heating"]].copy()
        def block_for(cat):
            try:
                return "Heizung" if bool(cat_meta.loc[cat, "is_heating"]) else "Betriebskosten"
            except Exception:
                return "Betriebskosten"
        my_details["block"] = my_details["category"].apply(block_for)
        sum_by_block = my_details.groupby("block")[ ["net","vat_amount","gross"] ].sum().round(2)

        # Vorauszahlungen (Payments NK/Heizung)
        q_adv = text("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE lease_id = :lid AND strftime('%Y', pay_date) = :yr AND category IN ('NK','Heizung')")
        adv = float(pd.read_sql(q_adv, engine, params={"lid": int(sel["lease_id"]), "yr": str(y)})["s"].iloc[0] or 0.0)
        total_bk = float(my_details["gross"].sum())
        saldo = total_bk - adv

        # Info-DF
        info = pd.DataFrame([{
            t("property","Objekt"): prop_choice,
            t("unit_label","Wohnung"): sel["unit_label"],
            t("tenant","Mieter"): sel["tenant"] or "",
            t("year","Jahr"): int(y),
            t("total_costs","Umlagefähige Kosten (€)"): round(total_bk,2),
            t("advances","Vorauszahlungen (€)"): round(adv,2),
            t("balance","Saldo (€)"): round(saldo,2)
        }])

        # Excel-Export mit Layout
        fname = f"BKA_{y}_{sel['unit_label']}.xlsx".replace(" ", "_")
        data = None; mime = None
        try:
            import xlsxwriter
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                # Sheet Abrechnung
                wb = writer.book
                ws = wb.add_worksheet("Abrechnung")
                writer.sheets["Abrechnung"] = ws

                # Formats
                fmt_title = wb.add_format({"bold": True, "font_size": 14})
                fmt_bold = wb.add_format({"bold": True})
                fmt_cur = wb.add_format({"num_format": '#,##0.00" €"'})
                fmt_small = wb.add_format({"font_size": 9, "italic": True, "align": "right"})

                # Logo
                logo = find_logo_path()
                if logo:
                    try:
                        ws.insert_image(0, 0, logo, {"x_scale": 0.5, "y_scale": 0.5})
                    except Exception:
                        pass

                ws.write(0, 3, t("operating_costs_statement","Betriebskostenabrechnung"), fmt_title)
                ws.write(2, 0, t("property","Objekt"), fmt_bold); ws.write(2, 1, str(prop_choice))
                ws.write(3, 0, t("unit_label","Wohnung"), fmt_bold); ws.write(3, 1, str(sel["unit_label"]))
                ws.write(4, 0, t("tenant","Mieter"), fmt_bold); ws.write(4, 1, str(sel["tenant"] or ""))
                ws.write(5, 0, t("year","Jahr"), fmt_bold); ws.write(5, 1, int(y))

                ws.write(7, 0, "Betriebskosten", fmt_bold)
                ws.write(7, 1, float(sum_by_block.loc["Betriebskosten","net"]) if "Betriebskosten" in sum_by_block.index else 0.0, fmt_cur)
                ws.write(7, 2, float(sum_by_block.loc["Betriebskosten","vat_amount"]) if "Betriebskosten" in sum_by_block.index else 0.0, fmt_cur)
                ws.write(7, 3, float(sum_by_block.loc["Betriebskosten","gross"]) if "Betriebskosten" in sum_by_block.index else 0.0, fmt_cur)

                ws.write(8, 0, "Heizung", fmt_bold)
                ws.write(8, 1, float(sum_by_block.loc["Heizung","net"]) if "Heizung" in sum_by_block.index else 0.0, fmt_cur)
                ws.write(8, 2, float(sum_by_block.loc["Heizung","vat_amount"]) if "Heizung" in sum_by_block.index else 0.0, fmt_cur)
                ws.write(8, 3, float(sum_by_block.loc["Heizung","gross"]) if "Heizung" in sum_by_block.index else 0.0, fmt_cur)

                ws.write(10, 0, t("total_costs","Umlagefähige Kosten (€)"), fmt_bold); ws.write(10, 1, float(total_bk), fmt_cur)
                ws.write(11, 0, t("advances","Vorauszahlungen (€)"), fmt_bold); ws.write(11, 1, float(adv), fmt_cur)
                ws.write(12, 0, t("balance","Saldo (€)"), fmt_bold); ws.write(12, 1, float(saldo), fmt_cur)

                ws.set_column(0, 0, 28); ws.set_column(1, 3, 20)
                ws.set_footer("&R" + t("footer_company","Erstellt mit Immobilien-Manager"))

                # Sheet Details
                det = my_details.groupby("category")[ ["net","vat_amount","gross"] ].sum().reset_index().round(2)
                det = det.rename(columns={"category": t("category","Kategorie"), "net": t("net","Netto (€)"), "vat_amount": t("vat","USt (€)"), "gross": t("gross","Brutto (€)")})
                det.to_excel(writer, sheet_name="Details", index=False)
                ws2 = writer.sheets["Details"]; ws2.set_column(0, 0, 28); ws2.set_column(1, 3, 18)

            data = buf.getvalue(); mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception:
            # Fallback CSV
            buf = io.StringIO()
            info.to_csv(buf, index=False); buf.write("\n"); 
            my_details.groupby("category")[ ["net","vat_amount","gross"] ].sum().reset_index().to_csv(buf, index=False)
            data = buf.getvalue().encode("utf-8"); mime = "text/csv"; fname = f"BKA_{y}_{sel['unit_label']}.csv".replace(" ", "_")

        st.download_button(t("download_statement","Abrechnung herunterladen"), data=data, file_name=fname, mime=mime)

        # PDF Export (ReportLab -> fallback WeasyPrint -> else Hinweis)
        pdf_bytes = None
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.lib.utils import ImageReader

            bufp = io.BytesIO()
            c = canvas.Canvas(bufp, pagesize=A4)
            w, h = A4

            # Logo
            logo = find_logo_path()
            if logo:
                try:
                    c.drawImage(ImageReader(logo), 15*mm, h-30*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Header
            c.setFont("Helvetica-Bold", 14)
            c.drawString(60*mm, h-20*mm, t("operating_costs_statement","Betriebskostenabrechnung"))
            c.setFont("Helvetica", 10)
            c.drawString(15*mm, h-40*mm, f"{t('property','Objekt')}: {prop_choice}")
            c.drawString(15*mm, h-46*mm, f"{t('unit_label','Wohnung')}: {sel['unit_label']}")
            c.drawString(15*mm, h-52*mm, f"{t('tenant','Mieter')}: {sel['tenant'] or ''}")
            c.drawString(15*mm, h-58*mm, f"{t('year','Jahr')}: {int(y)}")

            ycur = h-70*mm
            def line(lbl, val):
                nonlocal ycur
                c.setFont("Helvetica-Bold", 10); c.drawString(15*mm, ycur, lbl)
                c.setFont("Helvetica", 10); c.drawRightString(180*mm, ycur, f"{val:,.2f} €".replace(',', 'X').replace('.', ',').replace('X','.'))
                ycur -= 6*mm

            bk_net = float(sum_by_block.loc["Betriebskosten","net"]) if "Betriebskosten" in sum_by_block.index else 0.0
            bk_vat = float(sum_by_block.loc["Betriebskosten","vat_amount"]) if "Betriebskosten" in sum_by_block.index else 0.0
            bk_gro = float(sum_by_block.loc["Betriebskosten","gross"]) if "Betriebskosten" in sum_by_block.index else 0.0
            hz_net = float(sum_by_block.loc["Heizung","net"]) if "Heizung" in sum_by_block.index else 0.0
            hz_vat = float(sum_by_block.loc["Heizung","vat_amount"]) if "Heizung" in sum_by_block.index else 0.0
            hz_gro = float(sum_by_block.loc["Heizung","gross"]) if "Heizung" in sum_by_block.index else 0.0

            line("Betriebskosten (Netto)", bk_net)
            line("Betriebskosten (USt)", bk_vat)
            line("Betriebskosten (Brutto)", bk_gro)
            line("Heizung (Netto)", hz_net)
            line("Heizung (USt)", hz_vat)
            line("Heizung (Brutto)", hz_gro)
            line(t("advances","Vorauszahlungen (€)"), adv)
            line(t("balance","Saldo (€)"), saldo)

            c.setFont("Helvetica-Oblique", 8)
            c.drawRightString(200*mm, 10*mm, t("footer_company","Erstellt mit Immobilien-Manager"))
            c.showPage(); c.save()
            pdf_bytes = bufp.getvalue()
        except Exception:
            try:
                from weasyprint import HTML
                html = f"""
                <h2>{t('operating_costs_statement','Betriebskostenabrechnung')}</h2>
                <p><b>{t('property','Objekt')}:</b> {prop_choice}<br/>
                <b>{t('unit_label','Wohnung')}:</b> {sel['unit_label']}<br/>
                <b>{t('tenant','Mieter')}:</b> {sel['tenant'] or ''}<br/>
                <b>{t('year','Jahr')}:</b> {int(y)}</p>
                <table border='1' cellspacing='0' cellpadding='4'>
                <tr><th>Block</th><th>Netto (€)</th><th>USt (€)</th><th>Brutto (€)</th></tr>
                <tr><td>Betriebskosten</td><td>{sum_by_block.get('net',{}).get('Betriebskosten',0):.2f}</td><td>{sum_by_block.get('vat_amount',{}).get('Betriebskosten',0):.2f}</td><td>{sum_by_block.get('gross',{}).get('Betriebskosten',0):.2f}</td></tr>
                <tr><td>Heizung</td><td>{sum_by_block.get('net',{}).get('Heizung',0):.2f}</td><td>{sum_by_block.get('vat_amount',{}).get('Heizung',0):.2f}</td><td>{sum_by_block.get('gross',{}).get('Heizung',0):.2f}</td></tr>
                </table>
                <p><b>{t('advances','Vorauszahlungen (€)')}:</b> {adv:.2f}<br/>
                <b>{t('balance','Saldo (€)')}:</b> {saldo:.2f}</p>
                """
                pdf_bytes = HTML(string=html).write_pdf()
            except Exception:
                pdf_bytes = None

        if pdf_bytes:
            st.download_button(t("download_pdf","PDF herunterladen"), data=pdf_bytes, file_name=f"BKA_{y}_{sel['unit_label']}.pdf".replace(" ", "_"), mime="application/pdf")
        else:
            st.caption(t("pdf_unavailable","PDF-Erzeugung nicht verfügbar. Bitte 'reportlab' oder 'weasyprint' installieren."))

