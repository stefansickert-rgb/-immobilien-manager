import streamlit as st
import datetime as dt
from core.db import SessionCtx, Lease, Unit
from core.queries import df_units, df_tenants, df_leases, reset_caches
from core.i18n import t

st.header(t("leases"))

st.markdown("""
<style>
h3.page-head { margin-top:.2rem; margin-bottom:.4rem; }
div[data-testid="stPopover"] > div > button{
  height:2.2rem; min-width:2.2rem; padding:0 .35rem;
  display:flex; align-items:center; justify-content:center; border-radius:.6rem;
}
div[data-testid="stPopover"] > div > button p{ margin:0; line-height:1; font-size:1.05rem; }
div[data-testid="stPopover"] svg{ margin-left:.15rem; transform:translateY(1px); }
</style>
""", unsafe_allow_html=True)

def _popover_or_expander(container, label, help_text):
    if hasattr(st, "popover"): return container.popover(label, help=help_text)
    return container.expander(help_text, expanded=False)

def _add_form(container):
    units, tenants = df_units(), df_tenants()
    if units.empty or tenants.empty:
        st.info(t("need_units_tenants_first")); return
    with container.form("add_lease"):
        c1, c2, c3 = st.columns(3)
        with c1:
            u_map = {f"#{row['id']} – {row['unit_label']}": int(row['id']) for _, row in units.iterrows()}
            unit_key = st.selectbox(t("unit") + "*", list(u_map.keys()))
            start_date = st.date_input(t("start_date") + "*", value=dt.date.today())
            end_date = st.date_input(t("end_date_optional"), value=None)
        with c2:
            t_map = {f"#{row['id']} – {row['full_name']}": int(row['id']) for _, row in tenants.iterrows()}
            tenant_key = st.selectbox(t("tenant") + "*", list(t_map.keys()))
            rent_cold = st.number_input(t("rent_cold") + "*", min_value=0.0, step=10.0, format="%f")
            rent_warm = st.number_input(t("rent_warm"), min_value=0.0, step=10.0, format="%f")
        with c3:
            deposit = st.number_input(t("deposit"), min_value=0.0, step=50.0, format="%f")
        submitted = st.form_submit_button(t("save"))
    if submitted:
        with SessionCtx() as s:
            lease = Lease(
                unit_id=u_map[unit_key], tenant_id=t_map[tenant_key], start_date=start_date,
                end_date=end_date if end_date else None, rent_cold=rent_cold, rent_warm=rent_warm or None,
                deposit=deposit or None
            )
            s.add(lease)
            u = s.get(Unit, lease.unit_id)
            if u: u.is_rented = True; s.add(u)
            s.commit()
        reset_caches(); st.success(t("created"))

def _edit_form(container):
    leases = df_leases()
    if leases.empty:
        st.info(t("no_leases")); return
    options = {f"#{row['id']} – Whg {row['unit_label']} / {row['tenant_name']}": int(row['id']) for _, row in leases.iterrows()}
    sel = container.selectbox(t("select_lease"), list(options.keys()))
    sel_id = options[sel]
    with SessionCtx() as s:
        l = s.get(Lease, sel_id)
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button(t("end_lease_today")):
                l.end_date = dt.date.today()
                if l.unit: l.unit.is_rented = False; s.add(l.unit)
                s.add(l); s.commit(); reset_caches(); st.success(t("changes_saved"))
        with c2:
            if st.button(t("delete_lease"), type="secondary"):
                s.delete(l); s.commit(); reset_caches(); st.success(t("deleted"))

# Kopfzeile
h_left, h_icon1, h_icon2 = st.columns([1, 0.06, 0.06])
with h_left:  st.markdown(f"<h3 class='page-head'>{t('leases')}</h3>", unsafe_allow_html=True)
with h_icon1: 
    with _popover_or_expander(st, "➕", t("new_lease")): _add_form(st)
with h_icon2: 
    with _popover_or_expander(st, "🛠️", t("select_lease")): _edit_form(st)

# Tabelle
_df = df_leases().copy()

# Lokalisierte Tabelle mit Datums-/€-Format und Mieter-Link (gleiches Tab)
import pandas as pd
_df = df_leases().copy()
if not _df.empty:
    # Datum -> nur Datum
    for dcol in ["start_date","end_date"]:
        if dcol in _df.columns:
            _df[dcol] = pd.to_datetime(_df[dcol], errors="coerce").dt.date
    # €-Format
    def _fmt_eur(x):
        try:
            return f"{float(x):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return x
    for mcol in ["rent_cold","rent_warm","deposit"]:
        if mcol in _df.columns:
            _df[mcol] = _df[mcol].apply(_fmt_eur)

    # Mietername -> Link auf Mieter-Detail
    if "tenant_name" in _df.columns and "tenant_id" in _df.columns:
        _df["tenant_name"] = _df.apply(lambda r: f'<a target="_self" href="/Mieter?tenant_id={int(r["tenant_id"])}#tenant">{r["tenant_name"]}</a>', axis=1)
    if "unit_label" in _df.columns and "unit_id" in _df.columns:
        _df["unit_label"] = _df.apply(lambda r: f'<a target="_self" href="/Immobilien?unit_id={int(r["unit_id"])}#unit">{r["unit_label"]}</a>', axis=1)

    # Reihenfolge und Header
    order = [c for c in ["id","unit_label","tenant_name","start_date","end_date","rent_cold","rent_warm","deposit"] if c in _df.columns]
    if not order:
        order = _df.columns.tolist()
    header_map = {
        "id": "ID",
        "unit_label": t("unit_label","Wohnung"),
        "tenant_name": t("tenant","Mieter"),
        "start_date": t("start_date","Start"),
        "end_date": t("end_date","Ende"),
        "rent_cold": t("rent_cold","Kaltmiete (€)"),
        "rent_warm": t("rent_warm","Warmmiete (€)"),
        "deposit": t("deposit","Kaution (€)"),
    }
    disp = _df[order].rename(columns={k:v for k,v in header_map.items() if k in _df.columns})
    st.markdown(disp.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.caption(t("no_leases","Keine Mietverträge vorhanden."))

