# Immobilien-Manager — v5.1.7

Cloud-fähige Streamlit-App zur Verwaltung von Objekten, Wohnungen, Mietern, Verträgen, Zahlungen und Betriebskosten.

## Deployment (Streamlit Community Cloud)
1. Repo/Branch `main` auswählen.
2. **Main file** auf `app.py` setzen.
3. **Deploy** klicken.

## Login
- Standard-Admin (falls nicht vorhanden): **hannes / hannes**
- Neue Nutzer: Startseite → Tab **Registrieren**.

## Sicherheit
- Inhalte der Seiten sind nur nach Login sichtbar (Server-Guard).
- Sidebar-Navigation ist ausgeloggt ausgeblendet (CSS-Toggle).

## Changelog
Siehe In-App-Seite **Version**. Aktueller Build: **v5.1.7** (2025-10-03 21:38:21).

## Requirements
Python 3.10+, Streamlit, SQLAlchemy, pandas, Pillow, bcrypt (siehe `requirements.txt`).
