import streamlit as st
import datetime as dt
from core.db import SessionCtx, Financing, Unit
from core.queries import df_units, df_financings, reset_caches
from core.i18n import t

st.header(t("financings"))

# ---------- Styling: Überschrift + Icons rechts, kompakte Popover ----------
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

# ---------- Formulare ----------
def _add_form(container):
    units = df_units()
    if units.empty:
        st.info(t("no_units")); return
    with container.form("add_financing"):
        c1, c2, c3 = st.columns(3)
        with c1:
            u_map = {f"#{row['id']} – {row['unit_label']}": int(row['id']) for _, row in units.iterrows()}
            unit_key = st.selectbox(t("unit") + "*", list(u_map.keys()))
            lender_name = st.text_input(t("lender_name") + "*")
            loan_number = st.text_input(t("loan_number"))
            start_date = st.date_input(t("start_date") + "*", value=dt.date.today())
        with c2:
            end_date = st.date_input(t("end_date_optional"), value=None)
            principal_amount = st.number_input(t("principal_amount") + "*", min_value=0.0, step=1000.0, format="%f")
            interest_rate = st.number_input(t("interest_rate"), min_value=0.0, step=0.1, format="%.3f")
            repayment_rate = st.number_input(t("repayment_rate"), min_value=0.0, step=0.1, format="%.3f")
        with c3:
            monthly_payment = st.number_input(t("monthly_payment"), min_value=0.0, step=10.0, format="%f")
            fixed_rate_until = st.date_input(t("fixed_rate_until"), value=None)
            purpose = st.text_input(t("purpose"))
            collateral = st.text_input(t("collateral"))
        notes = st.text_area(t("notes"))
        submitted = st.form_submit_button(t("save"))

    if submitted:
        if not lender_name.strip():
            st.error(t("please_enter_name"))
        else:
            with SessionCtx() as s:
                s.add(Financing(
                    unit_id=u_map[unit_key],
                    lender_name=lender_name.strip(),
                    loan_number=loan_number or None,
                    start_date=start_date,
                    end_date=end_date if end_date else None,
                    principal_amount=principal_amount,
                    interest_rate=interest_rate or None,
                    repayment_rate=repayment_rate or None,
                    monthly_payment=monthly_payment or None,
                    fixed_rate_until=fixed_rate_until if fixed_rate_until else None,
                    purpose=purpose or None,
                    collateral=collateral or None,
                    notes=notes or None,
                ))
                s.commit()
            reset_caches(); st.success(t("created"))

def _edit_form(container):
    fins = df_financings()
    if fins.empty:
        st.info(t("no_data")); return
    options = {f"#{row['id']} – {row.get('unit_label','?')} / {row.get('lender_name','?')}": int(row['id']) for _, row in fins.iterrows()}
    sel = container.selectbox(t("select_financing"), list(options.keys()))
    sel_id = options[sel]

    with SessionCtx() as s:
        f = s.get(Financing, sel_id)
        with container.form("edit_financing"):
            c1, c2, c3 = st.columns(3)
            with c1:
                units = df_units()
                u_map = {f"#{row['id']} – {row['unit_label']}": int(row['id']) for _, row in units.iterrows()}
                current_label = next((k for k,v in u_map.items() if v == f.unit_id), list(u_map.keys())[0])
                unit_key = st.selectbox(t("unit") + "*", list(u_map.keys()), index=list(u_map.keys()).index(current_label))
                f.lender_name = st.text_input(t("lender_name") + "*", value=f.lender_name or "")
                f.loan_number = st.text_input(t("loan_number"), value=f.loan_number or "")
                f.start_date = st.date_input(t("start_date") + "*", value=f.start_date)
            with c2:
                f.end_date = st.date_input(t("end_date_optional"), value=f.end_date)
                f.principal_amount = st.number_input(t("principal_amount") + "*", value=float(f.principal_amount or 0.0), step=1000.0, format="%f")
                f.interest_rate = st.number_input(t("interest_rate"), value=float(f.interest_rate or 0.0), step=0.1, format="%.3f")
                f.repayment_rate = st.number_input(t("repayment_rate"), value=float(f.repayment_rate or 0.0), step=0.1, format="%.3f")
            with c3:
                f.monthly_payment = st.number_input(t("monthly_payment"), value=float(f.monthly_payment or 0.0), step=10.0, format="%f")
                f.fixed_rate_until = st.date_input(t("fixed_rate_until"), value=f.fixed_rate_until)
                f.purpose = st.text_input(t("purpose"), value=f.purpose or "")
                f.collateral = st.text_input(t("collateral"), value=f.collateral or "")
            notes = st.text_area(t("notes"), value=f.notes or "")
            csave, cdel = st.columns([1,1])
            save = csave.form_submit_button(t("save"))
            delete = cdel.form_submit_button(t("delete_financing"), type="secondary")

        if save:
            f.unit_id = u_map[unit_key]
            f.notes = notes or None
            s.add(f); s.commit(); reset_caches(); st.success(t("changes_saved"))

        if delete:
            s.delete(f); s.commit(); reset_caches(); st.success(t("deleted"))

# ---------- Kopfzeile: Überschrift + Icons daneben ----------
h_left, h_icon1, h_icon2 = st.columns([1, 0.06, 0.06])
with h_left:  st.markdown(f"<h3 class='page-head'>{t('financings')}</h3>", unsafe_allow_html=True)
with h_icon1:
    with _popover_or_expander(st, "➕", t("new_financing")): _add_form(st)
with h_icon2:
    with _popover_or_expander(st, "🛠️", t("edit_delete_financing")): _edit_form(st)

# ---------- Tabelle ----------
_df = df_financings().copy()
if not _df.empty:
    preferred = [
        "id","unit_id","unit_label","lender_name","loan_number",
        "start_date","end_date","principal_amount","interest_rate","repayment_rate",
        "monthly_payment","fixed_rate_until","remaining_balance","purpose","collateral","notes",
    ]
    ordered = [c for c in preferred if c in _df.columns] + [c for c in _df.columns if c not in preferred]
    _df = _df[ordered]

cfg = {
    "id": st.column_config.NumberColumn(label="ID", width="small", format="%d"),
    "unit_id": st.column_config.NumberColumn(label=t("unit"), width="small", format="%d"),
    "unit_label": st.column_config.Column(label=t("unit_label")) if "unit_label" in _df.columns else None,
    "lender_name": st.column_config.Column(label=t("lender_name")),
    "loan_number": st.column_config.Column(label=t("loan_number")),
    "start_date": st.column_config.DateColumn(label=t("start_date")),
    "end_date": st.column_config.DateColumn(label=t("end_date_optional")),
    "principal_amount": st.column_config.NumberColumn(label=t("principal_amount"), format="€ %.2f"),
    "interest_rate": st.column_config.NumberColumn(label=t("interest_rate"), format="%.3f %%"),
    "repayment_rate": st.column_config.NumberColumn(label=t("repayment_rate"), format="%.3f %%"),
    "monthly_payment": st.column_config.NumberColumn(label=t("monthly_payment"), format="€ %.2f"),
    "fixed_rate_until": st.column_config.DateColumn(label=t("fixed_rate_until")),
    "remaining_balance": st.column_config.NumberColumn(label=t("remaining_balance"), format="€ %.2f") if "remaining_balance" in _df.columns else None,
    "purpose": st.column_config.Column(label=t("purpose")),
    "collateral": st.column_config.Column(label=t("collateral")),
    "notes": st.column_config.Column(label=t("notes")),
}
# None-Werte entfernen (Streamlit mag kein None in column_config)
cfg = {k:v for k,v in cfg.items() if v is not None}

st.dataframe(_df, use_container_width=True, hide_index=True, column_config=cfg)
