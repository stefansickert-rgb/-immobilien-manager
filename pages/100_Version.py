import streamlit as st
import pandas as pd
from core.i18n import t

st.header("Versionen")

# Schlanker, sauberer Changelog (ältere Einträge wurden konsolidiert)
HISTORY = [
    {"version": "5.1.0", "timestamp": "2025-10-03 17:02:32", "changes": "Login-Gate + Admin hannes/hannes"},
    
    {"version": "4.28.7", "timestamp": "2025-09-26 20:50:43", "changes": "Mieter: Demodaten komplett neu generiert (Telefon, E-Mail, Bemerkungen, Geburtsdatum, Avatar) und bestehende überschrieben."},
    
    {"version": "4.28.5", "timestamp": "2025-09-26 20:36:30", "changes": "Immobilien: Mietername in Wohnungs-Tabelle als Link zur Mieter-Detailansicht. Mieter: Tabelle mit klickbaren Namen und Detailbereich reaktiviert. DB: Tenant birth_date/photo Felder inkl. Migration."},
    
    {"version": "4.28.4", "timestamp": "2025-09-26 20:17:24", "changes": "Mietverträge: Wohnungsbezeichnung verlinkt auf Wohnungs-Detail (gleiches Tab)."},
    
    {"version": "4.28.3", "timestamp": "2025-09-26 20:03:18", "changes": "Mietverträge: Objektspalte ergänzt; Wohnung/Objekt/Mieter als Links (gleiches Tab). Immobilien: ?property_id Vorwahl unterstützt."},
    
    {"version": "4.28.2", "timestamp": "2025-09-26 19:40:46", "changes": "Mietverträge: lokalisierte Header; Start/Ende als Datum; Mieten/Kaution in €; Mietername verlinkt auf Mieter-Details (gleiches Tab)."},
    
    {"version": "4.26", "timestamp": "2025-09-20 23:17:17", "changes": "Betriebskosten: echte Verbrauchsverteilung (Wasser/Heizung) aus Zählern; Excel-Layout mit Logo/Fußzeile/Netto-USt-Brutto und Heiz-/NK-Blöcken; PDF-Export (ReportLab/WeasyPrint, falls verfügbar)."},
    {"version": "4.25", "timestamp": "2025-09-20 23:10:25", "changes": "Betriebskosten: Abrechnung je Mietpartei mit Excel/CSV-Export (Knopfdruck) hinzugefügt."},
    {"version": "4.24.2", "timestamp": "2025-09-20 22:56:39", "changes": "Betriebskosten: SQL-Parameterbindung auf SQLAlchemy text()+named params umgestellt (read_sql)."},
    {"version": "4.24.1", "timestamp": "2025-09-20 22:53:53", "changes": "Betriebskosten: SyntaxError behoben (nonlocal → parameterisierte Funktion)."},
    {"version": "4.24", "timestamp": "2025-09-20 22:49:53", "changes": "Neues Modul Betriebskosten: Kosten erfassen, Umlageschlüssel, Abrechnungsvorschau; DB-Tabellen & Seed-Kategorien."},
    {"version": "4.23", "timestamp": "2025-09-20 22:30:01", "changes": "Demodaten für Finanzierungen hinzugefügt; Dashboard mit dynamischem Diagramm (Miete/Zinsen/Tilgung/Sonstige/Cashflow)."},
    {"version": "4.22.1", "timestamp": "2025-09-20 22:20:31", "changes": "Kompatibilität: st.experimental_rerun() → st.rerun() (Fotos speichern & Einstellungen)."},
    {"version": "4.22", "timestamp": "2025-09-20 22:14:50", "changes": "Navigation verschlankt (02 Objekte/03 Wohnungen entfernt); Versionstabelle lokalisiert; Demo-Daten generiert."},
    {"version": "4.21", "timestamp": "2025-09-20 22:14:50", "changes": "Dashboard: Abschnitt 'Letzte Zahlungen' entfernt; Datumsvergleich auf pandas.Timestamp vereinheitlicht."},
    {"version": "4.20.4", "timestamp": "2025-09-20 18:11:59", "changes": "Dashboard: Abschnitt 'Letzte Zahlungen' endgültig entfernt."},
]

df = pd.DataFrame(HISTORY)

# Sortierung: neueste zuerst
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.sort_values(["timestamp","version"], ascending=[False, False]).reset_index(drop=True)

# Lokalisierte Spaltenüberschriften
df = df.rename(columns={"version": t("version", "Version"), "timestamp": t("date", "Datum"), "changes": t("changes", "Änderungen")})

st.dataframe(df, use_container_width=True, hide_index=True)
