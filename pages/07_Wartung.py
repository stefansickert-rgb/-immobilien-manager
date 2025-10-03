from core.auth import require_login; _authctx = require_login()
import streamlit as st
from core.db import SessionCtx, MaintenanceTask
from core.queries import df_properties, df_tasks, reset_caches
from core.i18n import t

st.header(t("tasks"))

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
    props = df_properties()
    if props.empty:
        st.info(t("no_properties")); return
    with container.form("add_task"):
        c1, c2, c3 = st.columns(3)
        with c1:
            prop_map = {f"#{row['id']} – {row['name']}": int(row['id']) for _, row in props.iterrows()}
            prop_label = st.selectbox(t("property") + "*", list(prop_map.keys()))
            title = st.text_input(t("task_title") + "*")
        with c2:
            status = st.selectbox(t("status"), [t("status_open"), t("status_in_progress"), t("status_done")])
            due_date = st.date_input(t("due_date"), value=None)
        with c3:
            cost_estimate = st.number_input(t("cost_estimate"), min_value=0.0, step=50.0, format="%f")
            notes = st.text_input(t("notes"))
        submitted = st.form_submit_button(t("save"))
    if submitted:
        if not title.strip(): st.error(t("please_enter_name"))
        else:
            with SessionCtx() as s:
                s.add(MaintenanceTask(
                    property_id=prop_map[prop_label], title=title.strip(), status=status,
                    due_date=due_date if due_date else None, cost_estimate=cost_estimate or None, notes=notes
                ))
                s.commit()
            reset_caches(); st.success(t("created"))

def _edit_form(container):
    tasks = df_tasks()
    if tasks.empty:
        st.info(t("no_tasks")); return
    options = {f"#{row['id']} – {row['title']}": int(row['id']) for _, row in tasks.iterrows()}
    sel = container.selectbox(t("select_task"), list(options.keys()))
    sel_id = options[sel]
    with SessionCtx() as s:
        tsk = s.get(MaintenanceTask, sel_id)
        with container.form("edit_task"):
            c1, c2, c3 = st.columns(3)
            with c1:
                props = df_properties()
                prop_map2 = {f"#{row['id']} – {row['name']}": int(row['id']) for _, row in props.iterrows()}
                current_key = next((k for k, v in prop_map2.items() if v == tsk.property_id), list(prop_map2.keys())[0])
                prop_label2 = st.selectbox(t("property") + "*", list(prop_map2.keys()),
                                           index=list(prop_map2.keys()).index(current_key))
                tsk.title = st.text_input(t("task_title") + "*", value=tsk.title)
            with c2:
                st_statuses = [t("status_open"), t("status_in_progress"), t("status_done")]
                tsk.status = st.selectbox(t("status"), st_statuses, index=st_statuses.index(tsk.status))
                tsk.due_date = st.date_input(t("due_date"), value=tsk.due_date)
            with c3:
                tsk.cost_estimate = st.number_input(t("cost_estimate"), value=float(tsk.cost_estimate or 0.0), step=50.0, format="%f")
                tsk.notes = st.text_input(t("notes"), value=tsk.notes or "")
            csave, cdel = st.columns([1,1])
            save = csave.form_submit_button(t("save"))
            delete = cdel.form_submit_button(t("delete"), type="secondary")
        if save:
            tsk.property_id = prop_map2[prop_label2]; s.add(tsk); s.commit(); reset_caches(); st.success(t("changes_saved"))
        if delete:
            s.delete(tsk); s.commit(); reset_caches(); st.success(t("deleted"))

# Kopfzeile
h_left, h_icon1, h_icon2 = st.columns([1, 0.06, 0.06])
with h_left:  st.markdown(f"<h3 class='page-head'>{t('tasks')}</h3>", unsafe_allow_html=True)
with h_icon1: 
    with _popover_or_expander(st, "➕", t("new_task")): _add_form(st)
with h_icon2: 
    with _popover_or_expander(st, "🛠️", t("edit_delete_task")): _edit_form(st)

# Tabelle
_df = df_tasks().copy()
if not _df.empty:
    preferred = ["id","property_id","title","status","due_date","cost_estimate","notes"]
    ordered = [c for c in preferred if c in _df.columns] + [c for c in _df.columns if c not in preferred]
    _df = _df[ordered]
cfg = {
    "id": st.column_config.NumberColumn(label="ID", width="small", format="%d"),
    "property_id": st.column_config.NumberColumn(label=t("property"), width="small", format="%d"),
    "title": st.column_config.Column(label=t("task_title")),
    "status": st.column_config.Column(label=t("status")),
    "due_date": st.column_config.DateColumn(label=t("due_date")),
    "cost_estimate": st.column_config.NumberColumn(label=t("cost_estimate"), format="€ %.2f"),
    "notes": st.column_config.Column(label=t("notes")),
}
st.dataframe(_df, use_container_width=True, hide_index=True, column_config=cfg)
