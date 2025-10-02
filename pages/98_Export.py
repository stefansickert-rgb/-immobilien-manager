import streamlit as st
from core.queries import export_excel
import datetime as dt
from core.i18n import t

st.header(t("export"))

st.markdown("""
<style>
h3.page-head { margin-top:.2rem; margin-bottom:.4rem; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h3 class='page-head'>{t('export')}</h3>", unsafe_allow_html=True)
st.write(t("export_desc"))

data = export_excel()
st.download_button(
    label=t("download_excel"),
    data=data,
    file_name=f"immobilien_export_{dt.date.today().isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
