from core.auth import require_login; _authctx = require_login()
import streamlit as st
from sqlalchemy import select, func
from core.db import SessionCtx, Tenant, Lease
from core.queries import df_tenants, df_leases, df_units, reset_caches
from core.i18n import t
import pandas as pd

st.header(t("tenants"))

def _get_query_params():
    try:
        return st.query_params
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}


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
    with container.form("add_tenant"):
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input(t("full_name") + "*")
            phone = st.text_input(t("phone"))
        with c2:
            email = st.text_input(t("email"))
            notes = st.text_area(t("notes"))
        submitted = st.form_submit_button(t("save"))
    if submitted:
        if not full_name.strip(): st.error(t("please_enter_name"))
        else:
            with SessionCtx() as s:
                s.add(Tenant(full_name=full_name.strip(), phone=phone, email=email, notes=notes)); s.commit()
            reset_caches(); st.success(t("created"))

def _edit_form(container):
    tenants = df_tenants()
    if tenants.empty:
        st.info(t("no_tenants")); return
    options = {f"#{row['id']} – {row['full_name']}": int(row['id']) for _, row in tenants.iterrows()}
    sel = container.selectbox(t("select_tenant"), list(options.keys()))
    sel_id = options[sel]
    with SessionCtx() as s:
        tnt = s.get(Tenant, sel_id)
        with container.form("edit_tenant"):
            c1, c2 = st.columns(2)
            with c1:
                tnt.full_name = st.text_input(t("full_name") + "*", value=tnt.full_name)
                tnt.phone = st.text_input(t("phone"), value=tnt.phone or "")
            with c2:
                tnt.email = st.text_input(t("email"), value=tnt.email or "")
                tnt.notes = st.text_area(t("notes"), value=tnt.notes or "")
            csave, cdel = st.columns([1,1])
            save = csave.form_submit_button(t("save"))
            delete = cdel.form_submit_button(t("delete"), type="secondary")
        if save:
            if not tnt.full_name.strip(): st.error(t("please_enter_name"))
            else:
                s.add(tnt); s.commit(); reset_caches(); st.success(t("changes_saved"))
        if delete:
            has_leases = s.execute(select(func.count(Lease.id)).where(Lease.tenant_id == tnt.id)).scalar_one()
            if has_leases: st.error(t("cannot_delete_units"))
            else:
                s.delete(tnt); s.commit(); reset_caches(); st.success(t("deleted"))

# Kopfzeile
h_left, h_icon1, h_icon2 = st.columns([1, 0.06, 0.06])
with h_left:  st.markdown(f"<h3 class='page-head'>{t('tenants')}</h3>", unsafe_allow_html=True)
with h_icon1: 
    with _popover_or_expander(st, "➕", t("new_tenant")): _add_form(st)
with h_icon2: 
    with _popover_or_expander(st, "🛠️", t("edit_delete_tenant")): _edit_form(st)

# Tabelle
_df = df_tenants().copy()
leases = df_leases(); units = df_units()
if leases is not None and not leases.empty:
    today = pd.Timestamp.today().normalize()
    leases['start_date'] = pd.to_datetime(leases['start_date'], errors='coerce').dt.normalize()
    leases['end_date'] = pd.to_datetime(leases['end_date'], errors='coerce').dt.normalize()
    active = leases[(leases['start_date']<=today) & (leases['end_date'].isna() | (leases['end_date']>=today))]
    unit_map = {int(r['id']): r.get('unit_label') for _, r in units.iterrows()} if (units is not None and not units.empty) else {}
    act_map = active.groupby('tenant_id').agg({'unit_id': list}).to_dict()['unit_id'] if not active.empty else {}
    def _active_units_for_tenant(tid:int):
        ids = act_map.get(int(tid)) or []
        labels = [unit_map.get(int(uid)) for uid in ids if unit_map.get(int(uid))]
        return ", ".join(labels)
    _df['Aktives Mietverhältnis'] = _df['id'].map(lambda tid: len(act_map.get(int(tid), []))>0)
    _df['Wohnung(en)'] = _df['id'].map(_active_units_for_tenant)
if not _df.empty:
    preferred = ["id","full_name","Aktives Mietverhältnis","Wohnung(en)","phone","email","notes"]
    ordered = [c for c in preferred if c in _df.columns] + [c for c in _df.columns if c not in preferred]
    _df = _df[ordered]
cfg = {
    "id": st.column_config.NumberColumn(label="ID", width="small", format="%d"),
    "full_name": st.column_config.Column(label=t("full_name")),
    "Aktives Mietverhältnis": st.column_config.CheckboxColumn(label="Aktiv", help="Mindestens ein laufender Mietvertrag"),
    "Wohnung(en)": st.column_config.Column(label="Wohnung(en)"),
    "phone": st.column_config.Column(label=t("phone")),
    "email": st.column_config.Column(label=t("email")),
    "notes": st.column_config.Column(label=t("notes")),
}


# Eine Tabelle mit anklickbaren Namen (öffnet Detail unten, kein neuer Tab)
_df_html = _df.copy()
if not _df_html.empty and 'id' in _df_html.columns and 'full_name' in _df_html.columns:
    # Name -> Link (gleiches Tab)
    _df_html['full_name'] = _df_html.apply(lambda r: f'<a target="_self" href="?tenant_id={int(r["id"])}#tenant">{r["full_name"]}</a>', axis=1)
    # Checkbox für aktives Mietverhältnis
    if 'Aktives Mietverhältnis' in _df_html.columns:
        _df_html['Aktives Mietverhältnis'] = _df_html['Aktives Mietverhältnis'].map(lambda v: f'<input type="checkbox" disabled {"checked" if bool(v) else ""} />')
    # Spaltenreihenfolge
    cols = [c for c in ['id','full_name','Aktives Mietverhältnis','Wohnung(en)','phone','email','notes'] if c in _df_html.columns]
    # Deutsche Überschriften
    header_map = {
        'id': 'ID',
        'full_name': 'Vollständiger Name',
        'phone': 'Telefonnummer',
        'email': 'E-Mail',
        'notes': 'Bemerkungen',
        'Aktives Mietverhältnis': 'Aktives Mietverhältnis',
        'Wohnung(en)': 'Wohnung(en)',
    }
    disp = _df_html[cols].rename(columns={k:v for k,v in header_map.items() if k in _df_html.columns})
    st.markdown(disp.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.caption('Keine Mieter vorhanden.')


# Detail-Ansicht
params = _get_query_params()
tid = None
if params:
    raw = params.get('tenant_id') or params.get('tenant') or params.get('t')
    if raw:
        try:
            tid = int(raw if isinstance(raw, str) else raw[0])
        except Exception:
            tid = None

st.markdown('---')
st.subheader('Details', anchor='tenant')
if tid:
    from core.db import Tenant
    with SessionCtx() as s:
        tnt = s.get(Tenant, int(tid))
        if not tnt:
            st.warning('Mieter nicht gefunden.')
        else:
            st.markdown(f"### {tnt.full_name}")
            c1, c2 = st.columns([2,1])
            with c1:
                st.write('**Telefon:**', tnt.phone or '–')
                st.write('**E-Mail:**', tnt.email or '–')
                st.write('**Notiz:**', tnt.notes or '–')
                bd_val = pd.to_datetime(tnt.birth_date).date() if getattr(tnt,'birth_date', None) else None
                bd = st.date_input('Geburtsdatum', value=bd_val, key=f'bd_{tid}')
            with c2:
                if getattr(tnt,'photo', None):
                    st.image(tnt.photo, caption=getattr(tnt,'photo_filename', None) or 'Foto', use_container_width=True)
                up = st.file_uploader('Neues Foto hochladen', type=['png','jpg','jpeg','webp'], key=f'tphoto_{tid}')
            # aktiver Mietvertrag
            leases = df_leases()
            active = None
            if leases is not None and not leases.empty and 'tenant_id' in leases.columns:
                dfL = leases[leases['tenant_id']==int(tid)].copy()
                if not dfL.empty:
                    dfL['start_date'] = pd.to_datetime(dfL['start_date'], errors='coerce').dt.normalize()
                    dfL['end_date'] = pd.to_datetime(dfL['end_date'], errors='coerce').dt.normalize()
                    today = pd.Timestamp.today().normalize()
                    act = dfL[(dfL['start_date']<=today) & ((dfL['end_date'].isna()) | (dfL['end_date']>=today))]
                    if not act.empty:
                        active = act.iloc[0].to_dict()
            if active:
                st.success(f"Aktiver Mietvertrag: #{active['id']} – Wohnung {active.get('unit_label') or active.get('unit_id')} (Start {active['start_date'].date()})")
                try:
                    st.page_link('pages/05_Mietvertraege.py', label='Zum Mietverträge-Bereich')
                except Exception:
                    pass
            else:
                st.info('Kein aktiver Mietvertrag gefunden.')
            colA, colB = st.columns([1,1])
            if colA.button('Änderungen speichern', key=f'save_{tid}'):
                with SessionCtx() as s2:
                    obj = s2.get(Tenant, int(tid))
                    obj.birth_date = pd.to_datetime(bd).date() if bd else None
                    s2.commit()
                reset_caches(); st.success('Gespeichert.')
            if colB.button('Foto speichern', key=f'save_photo_{tid}') and up is not None:
                content = up.read()
                with SessionCtx() as s3:
                    obj = s3.get(Tenant, int(tid))
                    obj.photo = content
                    obj.photo_filename = up.name
                    s3.commit()
                reset_caches(); st.success('Foto gespeichert.'); st.rerun()
else:
    st.caption('Tipp: In der Tabelle auf einen Namen klicken, um Details zu öffnen.')
