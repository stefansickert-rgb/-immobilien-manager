# core/queries.py  — FIXED imports

import pandas as pd
import streamlit as st
from sqlalchemy import select

from .db import (
    SessionCtx, get_engine,
    Property, Unit, Tenant, Lease, Payment, MaintenanceTask,
    Financing,            # falls du "Finanzierungen" nutzt
    UnitPhoto, Radiator, Meter, MeterReading  # Detailseite Wohnung
)


@st.cache_data(ttl=2)
def df_properties() -> pd.DataFrame:
    with SessionCtx() as s:
        rows = s.execute(select(Property)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_units() -> pd.DataFrame:
    with SessionCtx() as s:
        rows = s.execute(select(Unit)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_tenants() -> pd.DataFrame:
    with SessionCtx() as s:
        rows = s.execute(select(Tenant)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_leases() -> pd.DataFrame:
    with SessionCtx() as s:
        rows = s.execute(select(Lease)).scalars().all()
        data = []
        for r in rows:
            row = r.as_dict()
            row["unit_label"] = r.unit.unit_label if r.unit else None
            row["tenant_name"] = r.tenant.full_name if r.tenant else None
            row["property_id"] = (r.unit.property.id if (r.unit and r.unit.property) else None)
            row["property_name"] = (r.unit.property.name if (r.unit and r.unit.property) else None)
            data.append(row)
        df = pd.DataFrame(data)
        if not df.empty:
            df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce").dt.normalize()
            df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce").dt.normalize()
        return df

@st.cache_data
def df_payments() -> pd.DataFrame:
    df = pd.read_sql_table("payments", get_engine())
    if "pay_date" in df.columns:
        df["pay_date"] = pd.to_datetime(df["pay_date"]).dt.normalize()
    elif "date" in df.columns:
        df["pay_date"] = pd.to_datetime(df["date"]).dt.normalize(); df = df.drop(columns=["date"])
    elif "payment_date" in df.columns:
        df["pay_date"] = pd.to_datetime(df["payment_date"]).dt.normalize()
    else:
        df["pay_date"] = pd.NaT
    return df

@st.cache_data(ttl=2)
def df_tasks() -> pd.DataFrame:
    with SessionCtx() as s:
        rows = s.execute(select(MaintenanceTask)).scalars().all()
        data = []
        for r in rows:
            row = r.as_dict()
            row["property_name"] = r.property.name if r.property else None
            data.append(row)
        return pd.DataFrame(data)
    
@st.cache_data(ttl=2)
def df_unit_photos(unit_id: int):
    with SessionCtx() as s:
        rows = s.execute(select(UnitPhoto).where(UnitPhoto.unit_id == unit_id)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_radiators(unit_id: int):
    with SessionCtx() as s:
        rows = s.execute(select(Radiator).where(Radiator.unit_id == unit_id)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_meters(unit_id: int):
    with SessionCtx() as s:
        rows = s.execute(select(Meter).where(Meter.unit_id == unit_id)).scalars().all()
        return pd.DataFrame([r.as_dict() for r in rows])

@st.cache_data(ttl=2)
def df_meter_readings(meter_id: int):
    with SessionCtx() as s:
        rows = s.execute(select(MeterReading).where(MeterReading.meter_id == meter_id)).scalars().all()
        df = pd.DataFrame([r.as_dict() for r in rows])
        if not df.empty:
            df["read_date"] = pd.to_datetime(df["read_date"]).dt.normalize()
        return df


def reset_caches():
    df_properties.clear()
    df_units.clear()
    df_tenants.clear()
    df_leases.clear()
    df_payments.clear()
    df_tasks.clear()
    df_financings.clear()  
    df_unit_photos.clear()
    df_radiators.clear()
    df_meters.clear()
    df_meter_readings.clear()


@st.cache_data
def export_excel() -> bytes:
    dfs = {
        "properties": df_properties(),
        "units": df_units(),
        "tenants": df_tenants(),
        "leases": df_leases(),
        "payments": df_payments(),
        "maintenance_tasks": df_tasks(),
    }
    from io import BytesIO
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in dfs.items():
            (df if not df.empty else pd.DataFrame()).to_excel(writer, sheet_name=name, index=False)
    return out.getvalue()

@st.cache_data(ttl=2)
def df_financings():
    with SessionCtx() as s:
        rows = s.execute(select(Financing)).scalars().all()
        data = []
        for r in rows:
            row = r.as_dict()
            row["unit_label"] = r.unit.unit_label if r.unit else None
            data.append(row)
        df = pd.DataFrame(data)
        if not df.empty:
            for col in ["start_date", "end_date", "fixed_rate_until"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()
        return df
