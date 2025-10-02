import streamlit as st
import datetime as dt
from core.db import SessionCtx, Payment
from core.queries import df_leases, df_payments, reset_caches
from core.i18n import t

st.header(t("payments"))

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
    leases = df_leases()
    if leases.empty:
        st.info(t("need_lease_first")); return
    with container.form("add_payment"):
        c1, c2, c3 = st.columns(3)
        with c1:
            l_map = {f"#{row['id']} – Whg {row['unit_label']} / {row['tenant_name']}": int(row['id']) for _, row in leases.iterrows()}
            lease_key = st.selectbox(t("leases") + "*", list(l_map.keys()))
            pay_date = st.date_input(t("date") + "*", value=dt.date.today())
        with c2:
            amount = st.number_input(t("amount") + "*", min_value=0.0, step=10.0, format="%f")
            category = st.selectbox(t("category"), [t("cat_rent"), t("cat_nk"), t("cat_deposit"), t("cat_other")])
        with c3:
            note = st.text_input(t("note"))
        submitted = st.form_submit_button(t("save"))
    if submitted:
        with SessionCtx() as s:
            s.add(Payment(lease_id=l_map[lease_key], pay_date=pay_date, amount=amount, category=category, note=note)); s.commit()
        reset_caches(); st.success(t("payment_recorded"))

# Kopfzeile (bei Zahlungen reicht 1 Icon: Zahlung erfassen)
h_left, h_icon = st.columns([1, 0.06])
with h_left: st.markdown(f"<h3 class='page-head'>{t('payments')}</h3>", unsafe_allow_html=True)
with h_icon:
    with _popover_or_expander(st, "➕", t("record_payment")): _add_form(st)

# Tabelle
_df = df_payments().copy()
if not _df.empty:
    preferred = ["id","lease_id","pay_date","amount","category","note"]
    ordered = [c for c in preferred if c in _df.columns] + [c for c in _df.columns if c not in preferred]
    _df = _df[ordered]
cfg = {
    "id": st.column_config.NumberColumn(label="ID", width="small", format="%d"),
}
if "pay_date" in _df.columns: cfg["pay_date"] = st.column_config.DateColumn(label=t("date"))
if "amount" in _df.columns: cfg["amount"] = st.column_config.NumberColumn(label=t("amount"), format="€ %.2f")
if "category" in _df.columns: cfg["category"] = st.column_config.Column(label=t("category"))
if "note" in _df.columns: cfg["note"] = st.column_config.Column(label=t("note"))
st.dataframe(_df, use_container_width=True, hide_index=True, column_config=cfg)
