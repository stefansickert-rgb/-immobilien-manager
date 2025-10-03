from __future__ import annotations
from sqlalchemy import ( Column, Integer, String, Float, Boolean, Date, ForeignKey, LargeBinary, create_engine )
from sqlalchemy.orm import declarative_base, relationship, Session, sessionmaker

import streamlit as st
import datetime as dt


DB_URL = "sqlite:///data.db"

# Engine/Sessionmaker cachen
@st.cache_resource
def get_engine():
    return create_engine(DB_URL, future=True)

@st.cache_resource
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), future=True, expire_on_commit=False)

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# --------------------
# Modelle
# --------------------
# --- Property-Modell (neue Felder) ---
class Property(BaseModel):
    __tablename__ = "properties"
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    city = Column(String, nullable=True)
    purchase_price = Column(Float, nullable=True)
    size_sqm = Column(Float, nullable=True)
    year_built = Column(Integer, nullable=True)                 # ← NEU
    ownership_transfer_date = Column(Date, nullable=True)       # ← NEU
    notes = Column(String, nullable=True)

    units = relationship("Unit", back_populates="property", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="property", cascade="all, delete-orphan")
    owned_by_me = Column(Boolean, default=True)  # NEU: gehört mir?



class Unit(BaseModel):
    __tablename__ = "units"
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    unit_label = Column(String, nullable=False)
    rooms = Column(Float, nullable=True)
    living_area_sqm = Column(Float, nullable=True)
    rent_cold_current = Column(Float, nullable=True)
    is_rented = Column(Boolean, default=False)
    balcony = Column(Boolean, default=False)
    cellar = Column(Boolean, default=False)          # Keller
    storage_room = Column(Boolean, default=False)    # Abstellraum
    garage = Column(Boolean, default=False)
    parking_spot = Column(Boolean, default=False)    # PKW-Stellplatz
    property = relationship("Property", back_populates="units")
    leases = relationship("Lease", back_populates="unit", cascade="all, delete-orphan")
    owned_by_me = Column(Boolean, default=True)  # NEU: gehört mir?
    financings = relationship("Financing", back_populates="unit", cascade="all, delete-orphan")
    photos = relationship("UnitPhoto", back_populates="unit", cascade="all, delete-orphan")
    radiators = relationship("Radiator", back_populates="unit", cascade="all, delete-orphan")
    meters = relationship("Meter", back_populates="unit", cascade="all, delete-orphan")



class Tenant(BaseModel):
    __tablename__ = "tenants"
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    photo = Column(LargeBinary, nullable=True)
    photo_filename = Column(String, nullable=True)

    leases = relationship("Lease", back_populates="tenant", cascade="all, delete-orphan")

class Lease(BaseModel):
    __tablename__ = "leases"
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    rent_cold = Column(Float, nullable=False)
    rent_warm = Column(Float, nullable=True)
    deposit = Column(Float, nullable=True)

    unit = relationship("Unit", back_populates="leases")
    tenant = relationship("Tenant", back_populates="leases")
    payments = relationship("Payment", back_populates="lease", cascade="all, delete-orphan")

class Payment(BaseModel):
    __tablename__ = "payments"
    lease_id = Column(Integer, ForeignKey("leases.id"), nullable=False)
    pay_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False, default="Miete")
    note = Column(String, nullable=True)

    lease = relationship("Lease", back_populates="payments")

class MaintenanceTask(BaseModel):
    __tablename__ = "maintenance_tasks"
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="offen")
    due_date = Column(Date, nullable=True)
    cost_estimate = Column(Float, nullable=True)
    notes = Column(String, nullable=True)

    property = relationship("Property", back_populates="maintenance_tasks")

# ✅ NEU: Nutzerprofil
class UserProfile(BaseModel):
    __tablename__ = "user_profile"
    first_name = Column(String, nullable=True)
    last_name  = Column(String, nullable=True)
    email      = Column(String, nullable=True)
    avatar     = Column(LargeBinary, nullable=True)  # <— NEU

class Financing(BaseModel):
    __tablename__ = "financings"

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    lender_name = Column(String, nullable=False)         # Kreditgeber/Bank
    loan_number = Column(String, nullable=True)          # Darlehens-/Vorgangsnummer

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)               # optionales Vertragsende

    principal_amount = Column(Float, nullable=False)     # Darlehenssumme (Nominal)
    interest_rate = Column(Float, nullable=True)         # Sollzins in %
    repayment_rate = Column(Float, nullable=True)        # anfängliche Tilgung in %
    monthly_payment = Column(Float, nullable=True)       # mtl. Rate
    fixed_rate_until = Column(Date, nullable=True)       # Zinsbindung bis
    remaining_balance = Column(Float, nullable=True)     # Restschuld (optional)
    purpose = Column(String, nullable=True)              # Verwendungszweck
    collateral = Column(String, nullable=True)           # Sicherheit (z. B. GS-Nr.)
    notes = Column(String, nullable=True)

    # ORM-Backref
    unit = relationship("Unit", back_populates="financings")

class UnitPhoto(BaseModel):
    __tablename__ = "unit_photos"
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    filename = Column(String, nullable=True)
    image = Column(LargeBinary, nullable=False)  # gespeichertes Bild
    uploaded_at = Column(Date, nullable=False, default=dt.date.today)
    position = Column(Integer, nullable=True)  # Reihenfolge für Anzeige

    unit = relationship("Unit", back_populates="photos")


class Radiator(BaseModel):
    __tablename__ = "radiators"
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    label = Column(String, nullable=False)      # z.B. „WZ links“
    notes = Column(String, nullable=True)

    unit = relationship("Unit", back_populates="radiators")


class Meter(BaseModel):
    __tablename__ = "meters"
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    type = Column(String, nullable=False)       # "electricity" | "water"
    serial_number = Column(String, nullable=True)
    location = Column(String, nullable=True)

    unit = relationship("Unit", back_populates="meters")
    readings = relationship("MeterReading", back_populates="meter", cascade="all, delete-orphan")


class MeterReading(BaseModel):
    __tablename__ = "meter_readings"
    meter_id = Column(Integer, ForeignKey("meters.id"), nullable=False)
    read_date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)       # Zählerstand

    meter = relationship("Meter", back_populates="readings")




class CostCategory(BaseModel):
    __tablename__ = "cost_categories"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)          # default language label
    name_en = Column(String, nullable=True)        # optional English label
    allocation_method = Column(String, nullable=False, default="UNITS")  # AREA, UNITS, PERSONS, WATER_M3, HEAT_SPLIT_70_30, FIXED
    is_heating = Column(Boolean, default=False)

class OperatingCost(BaseModel):
    __tablename__ = "operating_costs"
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    category_code = Column(String, ForeignKey("cost_categories.code"), nullable=False)
    amount_gross = Column(Float, nullable=False)
    vat_rate = Column(Float, nullable=True)
    supplier = Column(String, nullable=True)
    invoice_no = Column(String, nullable=True)
    description = Column(String, nullable=True)
    document_path = Column(String, nullable=True)

class PropertySetting(BaseModel):
    __tablename__ = "property_settings"
    property_id = Column(Integer, ForeignKey("properties.id"), primary_key=True)
    heat_ratio_consumption = Column(Integer, nullable=False, default=70)  # % consumption vs base
    persons_default = Column(Integer, nullable=False, default=2)
    water_allocation_fallback = Column(String, nullable=False, default="PERSONS")

class UnitPersons(BaseModel):
    __tablename__ = "unit_persons"
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    year = Column(Integer, nullable=False)
    persons = Column(Integer, nullable=False, default=0)
# --------------------
# DB-Init & Session-Kontext
# --------------------
# --- init_db anpassen (Schema-Version erhöhen & Spalten nachziehen) ---
@st.cache_resource
def init_db(schema_version: int = 8):
    Base.metadata.create_all(get_engine())

    # Ensure optional Tenant columns exist
    try:
        with get_engine().begin() as con:
            cols = [r[1] for r in con.exec_driver_sql("PRAGMA table_info(tenants)").fetchall()]
            if 'birth_date' not in cols:
                con.exec_driver_sql("ALTER TABLE tenants ADD COLUMN birth_date DATE")
            if 'photo' not in cols:
                con.exec_driver_sql("ALTER TABLE tenants ADD COLUMN photo BLOB")
            if 'photo_filename' not in cols:
                con.exec_driver_sql("ALTER TABLE tenants ADD COLUMN photo_filename TEXT")
    except Exception:
        pass

    # Seed default cost categories and property settings
    try:
        with get_engine().begin() as con:
            # Seed categories if empty
            cnt = con.exec_driver_sql("SELECT COUNT(*) FROM cost_categories").scalar()
            if cnt is None or cnt == 0:
                seed = [
                    ('GRUNDSTEUER','Grundsteuer', 'Property tax', 'AREA', 0),
                    ('GEB_VERS','Gebäudeversicherung', 'Building insurance', 'AREA', 0),
                    ('HAUSSTROM','Allgemeinstrom', 'Common electricity', 'UNITS', 0),
                    ('REINIGUNG','Hausreinigung', 'Cleaning', 'UNITS', 0),
                    ('GARTEN','Gartenpflege', 'Garden', 'UNITS', 0),
                    ('MUELL','Müll', 'Waste', 'PERSONS', 0),
                    ('WASSER','Wasser/Abwasser', 'Water/Sewage', 'WATER_M3', 0),
                    ('HEIZ_BRENN','Heizung Brennstoff', 'Heating fuel', 'HEAT_SPLIT_70_30', 1),
                    ('HEIZ_WART','Heizung Wartung', 'Heating service', 'HEAT_SPLIT_70_30', 1),
                    ('SCHORN','Schornsteinfeger', 'Chimney sweep', 'HEAT_SPLIT_70_30', 1),
                    ('HAUSMEISTER','Hausmeister', 'Janitor', 'UNITS', 0),
                    ('SONSTIGE_BK','Sonstige BK', 'Other costs', 'UNITS', 0)
                ]
                for code,n_de,n_en,alloc,heat in seed:
                    con.exec_driver_sql(
                        "INSERT INTO cost_categories (code,name,name_en,allocation_method,is_heating) VALUES (?,?,?,?,?)",
                        (code,n_de,n_en,alloc,heat)
                    )
            # Ensure property_settings for all properties
            try:
                rows = con.exec_driver_sql("SELECT id FROM properties").fetchall()
                for (pid,) in rows:
                    ex = con.exec_driver_sql("SELECT 1 FROM property_settings WHERE property_id=?", (pid,)).fetchone()
                    if not ex:
                        con.exec_driver_sql("INSERT INTO property_settings (property_id,heat_ratio_consumption,persons_default,water_allocation_fallback) VALUES (?,?,?,?)", (pid,70,2,'PERSONS'))
            except Exception:
                pass
    except Exception:
        pass


    # Seed: Finanzierung für Whg 1 im Objekt Musterstraße 1 (idempotent)
    try:
        from sqlalchemy import select
        with get_engine().connect() as con:
            # Fetch property id
            pid = None
            try:
                rows = con.exec_driver_sql("SELECT id,label,name,address FROM properties").fetchall()
                for r in rows:
                    lbl = (r[1] or r[2] or "" ).lower()
                    addr = (r[3] or "").lower()
                    if "musterstraße 1" in lbl or "musterstraße 1" in addr:
                        pid = r[0]; break
            except Exception:
                pid = None
            if pid is not None:
                # find unit with unit_label like '1' or id=1 in that property
                rows = con.exec_driver_sql(f"SELECT id, unit_label FROM units WHERE property_id={pid}").fetchall()
                uid = None
                for r in rows:
                    ulbl = (r[1] or "").strip()
                    if ulbl == "1" or ulbl.lower().startswith("whg 1") or r[0] == 1:
                        uid = r[0]; break
                if uid is not None:
                    # check existing financing for this unit
                    rows = con.exec_driver_sql(f"SELECT COUNT(1) FROM financings WHERE unit_id={uid}").fetchone()
                    has = int(rows[0]) if rows else 0
                    if has == 0:
                        # insert demo financing
                        con.exec_driver_sql(
                            "INSERT INTO financings (unit_id, bank, interest_rate, principal_amount, start_date, end_date, monthly_payment) "
                            f"VALUES ({uid}, 'DemoBank', 3.2, 200000, date('now','-2 years'), NULL, 950)"
                        )

    except Exception as e:
        pass
    # Migration: UnitPhoto.position hinzufügen, falls fehlt
    try:
        eng = get_engine()
        with eng.connect() as con:
            cols = con.exec_driver_sql("PRAGMA table_info(unit_photos)").fetchall()
            colnames = {c[1] for c in cols}
            if 'position' not in colnames:
                con.exec_driver_sql("ALTER TABLE unit_photos ADD COLUMN position INTEGER")
    except Exception:
        pass

    # Lightweight migration: add Unit.notes if missing
    try:
        eng = get_engine()
        with eng.connect() as con:
            cols = con.exec_driver_sql("PRAGMA table_info(units)").fetchall()
            colnames = {c[1] for c in cols}
            if 'notes' not in colnames:
                con.exec_driver_sql("ALTER TABLE units ADD COLUMN notes TEXT")
    except Exception as _e:
        pass
    # falls du PRAGMA-basierte Migrationen hast (year_built, avatar, owned_by_me, features etc.),
    # bitte UNVERÄNDERT beibehalten – create_all legt 'financings' automatisch an, wenn sie fehlt.
    return True






class SessionCtx:
    def __enter__(self) -> Session:
        self._session = get_sessionmaker()()
        return self._session
    def __exit__(self, exc_type, exc, tb):
        self._session.close()

def seed_demo_tenants(limit: int = 14):
    """Füllt für bis zu `limit` vorhandene Mieter fehlende Felder (Telefon, E-Mail, Notiz,
Geburtsdatum, Foto) mit Demodaten. Existierende Werte werden nicht überschrieben."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        pil_ok = True
    except Exception:
        pil_ok = False

    import io, hashlib, random, datetime as _dt

    with SessionCtx() as s:
        rows = s.execute(select(Tenant).order_by(Tenant.id.asc())).scalars().all()
        cnt = 0
        for t in rows:
            if cnt >= limit:
                break
            changed = False

            # Phone
            if not (t.phone and t.phone.strip()):
                # pseudo-deutsches Format
                h = int(hashlib.sha256(t.full_name.encode('utf-8')).hexdigest(), 16)
                num = f"+49 151 {h % 900 + 100:03d} {h % 9000 + 1000:04d}"
                t.phone = num
                changed = True
            # Email
            if not (t.email and t.email.strip()):
                base = t.full_name.lower().replace(" ", ".").replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
                t.email = f"{base}@demo.example"
                changed = True
            # Notes
            if not t.notes:
                t.notes = "Demodaten automatisch ergänzt."
                changed = True
            # Birth date
            if not getattr(t, "birth_date", None):
                # 1960-01-01 .. 2002-12-31
                h = int(hashlib.md5(t.full_name.encode('utf-8')).hexdigest(), 16)
                year = 1960 + (h % 43)  # 1960..2002
                month = (h // 31) % 12 + 1
                day = (h // 97) % 28 + 1
                t.birth_date = _dt.date(year, month, day)
                changed = True
            # Photo
            if not getattr(t, "photo", None):
                if pil_ok:
                    # Avatar mit Initialen
                    initials = "".join([part[0].upper() for part in t.full_name.split() if part])[:2] or "M"
                    h = int(hashlib.sha256(t.full_name.encode('utf-8')).hexdigest(), 16)
                    bg = ( (h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF )
                    img = Image.new("RGB", (256,256), bg)
                    draw = ImageDraw.Draw(img)
                    fs = 110
                    try:
                        font = ImageFont.truetype("arial.ttf", fs)
                    except Exception:
                        font = ImageFont.load_default()
                    w, htxt = draw.textsize(initials, font=font)
                    draw.text(((256-w)/2, (256-htxt)/2), initials, fill=(255,255,255), font=font)
                    buf = io.BytesIO(); img.save(buf, format="PNG"); t.photo = buf.getvalue()
                    t.photo_filename = f"avatar_{t.id or 0}.png"
                    changed = True
            if changed:
                cnt += 1
        if cnt > 0:
            s.commit()
    return True



class User(BaseModel):
    __tablename__ = "users"
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=dt.date.today)


def ensure_admin_user(username: str, password_hash: str, role: str = "admin", email: str | None = None, full_name: str | None = None):
    with SessionCtx() as s:
        u = s.query(User).filter(User.username == username).one_or_none()
        if u is None:
            s.add(User(username=username, email=email, full_name=full_name or username, password_hash=password_hash, role=role, is_active=True))
            s.commit()
        else:
            if not u.password_hash:
                u.password_hash = password_hash
            if not u.role:
                u.role = role
            if not u.is_active:
                u.is_active = True
            s.commit()

def load_credentials_for_auth():
    with SessionCtx() as s:
        cred = {"usernames": {}}
        for u in s.query(User).filter(User.is_active == True).all():
            cred["usernames"][u.username] = {
                "name": u.full_name or u.username,
                "email": u.email or "",
                "password": u.password_hash,
            }
        return cred

def _post_models_create_all():
    try:
        Base.metadata.create_all(get_engine())
    except Exception:
        pass

_post_models_create_all()
