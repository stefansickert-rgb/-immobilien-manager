import streamlit as st
import pandas as pd
from core.queries import df_properties, df_units, df_leases, df_payments
from core.i18n import t

st.title(t("overview"))

# KPI tiles
c1, c2, c3, c4 = st.columns(4)
props, units, leases = df_properties(), df_units(), df_leases()

with c1:
    st.metric(t("properties_count"), 0 if props.empty else len(props))

with c2:
    st.metric(t("units_count"), 0 if units.empty else len(units))

with c3:
    today = pd.Timestamp.today().normalize()
    if leases.empty:
        active = 0
    else:
        le = leases.copy()
        le["start_date"] = pd.to_datetime(le.get("start_date"), errors="coerce")
        le["end_date"] = pd.to_datetime(le.get("end_date"), errors="coerce")
        start_ok = le["start_date"] <= today
        no_end = le["end_date"].isna()
        end_ok = (~no_end) & (le["end_date"] >= today)
        active = int((start_ok & (no_end | end_ok)).sum())
    st.metric(t("active_leases"), active)

with c4:
    monthly_cold_rent = 0.0
    if not leases.empty and "rent_cold" in leases.columns:
        le = leases.copy()
        le["start_date"] = pd.to_datetime(le.get("start_date"), errors="coerce")
        le["end_date"] = pd.to_datetime(le.get("end_date"), errors="coerce")
        start_ok = le["start_date"] <= today
        no_end = le["end_date"].isna()
        end_ok = (~no_end) & (le["end_date"] >= today)
        monthly_cold_rent = float(le.loc[start_ok & (no_end | end_ok), "rent_cold"].fillna(0).sum())
    st.metric(t("rent_cold_per_month", "Kaltmiete/Monat (€)"), f"{monthly_cold_rent:,.0f}".replace(",", "."))

# Monthly development (Miete / Zinsen / Tilgung / Cashflow v1)
pay = df_payments()
if pay is not None and not pay.empty:
    df = pay.copy()
    df["pay_date"] = pd.to_datetime(df.get("pay_date"), errors="coerce")
    df["month"] = df["pay_date"].dt.to_period("M").astype(str)

    cat = df.get("category").fillna("Sonstiges").astype(str)
    rent_label = t("cat_rent", "Miete")
    miete = df[cat.eq(rent_label)]
    zinsen = df[cat.eq("Zinsen")]
    tilgung = df[cat.eq("Tilgung")]
    sonstige = df[~(cat.eq(rent_label) | cat.eq("Zinsen") | cat.eq("Tilgung"))]

    def by_month(d):
        if d.empty or "amount" not in d.columns:
            return pd.Series(dtype=float)
        return d.groupby("month")["amount"].sum()

    miete_m = by_month(miete)
    zinsen_m = by_month(zinsen)
    tilgung_m = by_month(tilgung)
    sonstige_m = by_month(sonstige)

    all_months = sorted(set(miete_m.index) | set(zinsen_m.index) | set(tilgung_m.index) | set(sonstige_m.index))
    monat_df = pd.DataFrame(index=all_months)
    monat_df["Miete"] = miete_m.reindex(all_months, fill_value=0)
    monat_df["Zinsen"] = zinsen_m.reindex(all_months, fill_value=0)
    monat_df["Tilgung"] = tilgung_m.reindex(all_months, fill_value=0)
    monat_df["Sonstige"] = sonstige_m.reindex(all_months, fill_value=0)
    monat_df["Cashflow v1"] = monat_df["Miete"] - monat_df["Zinsen"] - monat_df["Sonstige"]

    if not monat_df.empty:
        st.markdown("### Monatliche Entwicklung (Miete / Zinsen / Tilgung / Cashflow v1)")
        st.dataframe(monat_df.sort_index(ascending=False), use_container_width=True)

    # --- Diagramm: auswählbare Kennzahlen ---
    chart_cols_all = ["Miete", "Zinsen", "Tilgung", "Sonstige", "Cashflow v1"]
    default_sel = ["Miete", "Cashflow v1"]
    sel = st.multiselect(t("chart_select", "Kennzahlen auswählen"), chart_cols_all, default=default_sel)
    if sel:
        chart_df = monat_df[sel].sort_index()
        chart_type = st.selectbox(t("chart_type", "Diagrammtyp"), ["Linie", "Balken"], index=0)
        st.markdown("### " + t("chart_title", "Zeitreihe"))
        if chart_type == "Linie":
            st.line_chart(chart_df, use_container_width=True)
        else:
            st.bar_chart(chart_df, use_container_width=True)

else:
    st.info("Noch keine Zahlungen erfasst.")
